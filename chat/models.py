from app.models import *
import shortuuid
from django.core.exceptions import ValidationError
from django.utils import timezone

def generate_unique_chatroom_name():
    while True:
        chatroom_name = shortuuid.uuid()[:20]
        if not ChatRoom.objects.filter(chatroom_name = chatroom_name).exists():
            return chatroom_name

class ChatRoom(models.Model):
    chatroom_name = models.CharField(max_length=20, default=generate_unique_chatroom_name)
    members = models.ManyToManyField(User, related_name='chatrooms')
    deleted_for = models.ManyToManyField(User, through='ChatRoomDelete', related_name='deleted_chatrooms', blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def mark_delete_for(self, user):
        ChatRoomDelete.objects.update_or_create(
            chatroom=self,
            user = user,
            defaults={'deleted_at': timezone.now()}
        )

    def clean(self):
        super().clean()
        if self.pk and self.members.count() > 2:
            raise ValidationError('Chat room cannot have more than 2 members.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        members = ''
        for member in self.members.all():
            members += f'{member.username} - '
        return members[:-2]

class ChatRoomDelete(models.Model):
    chatroom = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    deleted_at = models.DateTimeField()

    class Meta:
        unique_together = ('chatroom', 'user')

class ChatMessage(models.Model):
    chatroom = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sended_messages')
    receiver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='received_messages')
    body = models.TextField()
    image = models.ImageField(upload_to='messages', null=True, blank=True)
    is_viewed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.sender} : {self.body}'