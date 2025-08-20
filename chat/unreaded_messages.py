from .models import *

def count_unreaded_messages(request):
    unreaded_messages = None
    if request.user.is_authenticated:
        unreaded_messages = ChatMessage.objects.filter(receiver = request.user, is_viewed = False).count()
    
    return { 'unreaded_messages' : unreaded_messages }