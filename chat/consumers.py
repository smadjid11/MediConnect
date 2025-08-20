from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import json
from .models import *
import base64
from django.core.files.base import ContentFile
from django.forms.models import model_to_dict
from django.utils import timezone
import redis.asyncio as redis
from channels.db import database_sync_to_async
from django.conf import settings

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.user_id = self.user.id
        self.chatroom_name = self.scope['url_route']['kwargs']['chatroom_name']
        self.chatroom = await sync_to_async(ChatRoom.objects.get)(
            chatroom_name = self.chatroom_name
        )
        
        members = await sync_to_async(list)(self.chatroom.members.all())
        self.other_user = await sync_to_async(
            lambda: self.chatroom.members.exclude(id=self.user.id)
                   .first()
        )()

        if self.other_user:
            print(f"other user username : {self.other_user.username}")
        
        self.redis = await redis.from_url(settings.URL_REDIS_DB_1, decode_responses=True)
        
        await self.redis.hincrby(f'chatroom:{self.chatroom_name}:users', self.user.id, 1)

        await self.channel_layer.group_add(f"user_{self.user.id}", self.channel_name)

        await self.channel_layer.group_add(self.chatroom_name, self.channel_name)

        remaining = await self.redis.hget(f'chatroom:{self.chatroom_name}:users', self.user.id)
        

        if int(remaining) == 1 and self.other_user:
            # For Making Non messages viewed will viewed
            messages = await database_sync_to_async(list)(ChatMessage.objects.filter(
                chatroom=self.chatroom,
                sender=self.other_user,
                receiver=self.user,
                is_viewed=False
            ).only('id'))
            
            messages_ids = [msg.id for msg in messages]
            
            await database_sync_to_async(ChatMessage.objects.filter(
                id__in = messages_ids,
            ).update)(is_viewed=True)
            
            # Inside Chat
            await self.channel_layer.group_send(
                self.chatroom_name,
                {
                    'type' : 'update_new_viewed_messages',
                    'messages_ids' : messages_ids,
                    'viewer_id' : self.user.id,
                }
            )
            # Messages Page
            if messages_ids:
                await self.channel_layer.group_send(
                    f'{self.other_user.id}_notification_room',
                    {
                        'type' : 'update_new_viewed_messages',
                        'messages_ids' : messages_ids,
                        'viewer_id' : self.user.id,
                    }
                )
        
        await self.accept()

        await self.send(text_data=json.dumps({
            'type' : 'connection',
            'status' : 'connected',
        }))
    
    async def disconnect(self, code):
        if code == 4001:
            await self.redis.hdel(f'chatroom:{self.chatroom_name}:users', self.user_id)
        else:
            remaining = await self.redis.hincrby(f'chatroom:{self.chatroom_name}:users', self.user_id, -1)
            if remaining <= 0:
                await self.redis.hdel(f'chatroom:{self.chatroom_name}:users', self.user_id)
            
        await self.channel_layer.group_discard(self.chatroom_name, self.channel_name)
        await self.channel_layer.group_discard(f"user_{self.user_id}", self.channel_name)
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        type = data['type']
        
        if type == 'chat':
            if not await sync_to_async(lambda: User.objects.filter(id=self.other_user.id).exists())() or not await sync_to_async(lambda: User.objects.filter(id=self.user_id).exists())():
                return None
            
            body_message = data['body_message']
            image_base64  = data['image_message']
            
            image_file = None
            if image_base64:
                file_name = data['file_name']
                format, imgstr = image_base64.split(';base64,')  # split header of image
                ext = format.split('/')[-1]  # link: jpeg or png
                image_file = ContentFile(base64.b64decode(imgstr), name=f"{file_name}")
            
            message_sended = await sync_to_async(ChatMessage.objects.create)(
                chatroom = self.chatroom,
                sender = self.user,
                receiver = self.other_user,
                body = body_message,
                image = image_file,
            )

            # Check If Other User In Chat Room For Making New Messages Is Viewed By Him
            connections = await self.redis.hget(f'chatroom:{self.chatroom_name}:users', self.other_user.id)

            if connections:
                if int(connections) > 0:
                    message_sended.is_viewed = True
                    await sync_to_async(message_sended.save)()

            # Send to Only Chat Channel
            await self.channel_layer.group_send(
                self.chatroom_name,
                {
                    'type' : 'send_message',
                    'sender_id' : self.user.id,
                    'message_id' : message_sended.id,
                    'sending_message_id' : data['sending_message_id'],
                }
            )
            # Send to All Pages As Notification Except Chat Channels
            user_pfp_url = '/static/images/default-patient-pfp.jpg'
            speciality = None

            is_patient = await sync_to_async(lambda: hasattr(self.user, 'patientprofile'))()

            if is_patient:
                if await sync_to_async(lambda: self.user.patientprofile.avatar)():
                    user_pfp_url = await sync_to_async(lambda: self.user.patientprofile.avatar.url)()
            elif await sync_to_async(lambda: hasattr(self.user, 'doctorprofile'))():
                if await sync_to_async(lambda: self.user.doctorprofile.avatar)():
                    user_pfp_url = await sync_to_async(lambda: self.user.doctorprofile.avatar.url)()
                speciality = await sync_to_async(lambda: self.user.doctorprofile.speciality.name)()
            elif await sync_to_async(lambda: hasattr(self.user, 'adminprofile'))():
                if await sync_to_async(lambda: self.user.adminprofile.avatar)():
                    user_pfp_url = await sync_to_async(lambda: self.user.adminprofile.avatar.url)()
            
            other_user_is_online = False
            remaining = await self.redis.hget('online_room_users', self.other_user.id)
            if remaining and int(remaining) >= 1:
                other_user_is_online = True

            await self.channel_layer.group_send(
                f'{self.other_user.id}_notification_room',
                {
                    'type' : 'received_message',
                    'message_sender_id' : self.user.id,
                    'message_sended' : message_sended.body,
                    'message_id' : message_sended.id,
                    'user_pfp_url' : user_pfp_url,
                    'user_fullname' : self.user.first_name,
                    'user_speciality' : speciality,
                    'chatroom_name' : self.chatroom_name,
                    'other_user_is_online' : other_user_is_online,
                }
            )

        elif type == 'typing':
            is_typing = data['is_typing']

            if is_typing:
                await self.channel_layer.group_send(
                    self.chatroom_name,
                    {
                        'type' : 'update_typing_status',
                        'typer_id' : self.user.id,
                        'is_typing' : True,
                    }
                )
    
    async def send_message(self, event):
        sender = await sync_to_async(User.objects.get)(id = event['sender_id'])
        message = await sync_to_async(ChatMessage.objects.get)(id = event['message_id'])

        
        created = timezone.localtime(message.created)
        message_time = created.strftime("%b. %d, %Y, %I:%M %p").lstrip('0').replace('AM', 'a.m.').replace('PM', 'p.m.')

        message_url = None
        if message.image:
            message_url = message.image.url
        
        await self.send(text_data=json.dumps({
            'type' : 'chat',
            'i_am_sender' : sender.id == self.user.id,
            'message_id' : message.id,
            'body_message' : message.body,
            'image_message' : message_url,
            'created_message' : message_time,
            'message_is_viewed' : message.is_viewed,
            'sending_message_id' : event['sending_message_id'],
        }))

    async def update_new_viewed_messages(self, event):
        if self.user.id != event['viewer_id']:
            await self.send(text_data=json.dumps({
                'type' : 'update_new_viewed_messages',
                'messages_ids' : event['messages_ids'],
            }))

    async def update_typing_status(self, event):
        if self.user.id != event['typer_id']:
            await self.send(text_data=json.dumps({
                'type' : 'typing',
                'typer_id' : event['typer_id'],
                'is_typing' : event['is_typing'],
            }))

    async def force_disconnect(self, event):
        await self.close(code=4001)

class OnlineStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.online_room_name = 'online_room'
        self.user = self.scope['user']
        self.user_id = self.user.id
        self.redis = redis.from_url(settings.URL_REDIS_DB_1, decode_responses=True)

        await self.channel_layer.group_add(f"user_{self.user_id}", self.channel_name)
        await self.channel_layer.group_add(self.online_room_name, self.channel_name)

        await self.accept()

        remaining = await self.redis.hincrby('online_room_users', self.user.id, 1)

        if remaining == 1:
            if await sync_to_async(lambda: hasattr(self.user, 'patientprofile'))():
                await self.patient_profile_clear_last_online(self.user.patientprofile)
            await self.channel_layer.group_send(
                self.online_room_name, 
                {
                    'type' : 'update_online_status',
                    'user_new_status_id' : self.user.id,
                    'status' : 'connected',
                }
            )

        await self.send(text_data=json.dumps({
            'type' : 'connection',
            'status' : 'connected',
        }))

    async def disconnect(self, code):
        if code == 4001:
            await self.redis.hdel('online_room_users', self.user_id)
        else:
            remaining = await self.redis.hincrby('online_room_users', self.user_id, -1)

            if remaining <= 0:
                if await sync_to_async(lambda: hasattr(self.user, 'patientprofile'))():
                    await self.patient_profile_update_last_online(self.user.patientprofile)
                await self.redis.hdel('online_room_users', self.user.id)
                await self.channel_layer.group_send(
                    self.online_room_name, 
                    {
                        'type' : 'update_online_status',
                        'user_new_status_id' : self.user.id,
                        'status' : 'disconnected',
                    }
                )
            
        await self.channel_layer.group_discard(self.online_room_name, self.channel_name)
        await self.channel_layer.group_discard(f"user_{self.user_id}", self.channel_name)
    
    async def update_online_status(self, event):
        if self.user.id != event['user_new_status_id']:
            user_new_status = await database_sync_to_async(User.objects.get)(id=event['user_new_status_id'])
            
            has_shared_chatroom = await database_sync_to_async(
                lambda: ChatRoom.objects.filter(members=self.user).filter(members=user_new_status).exists()
            )()
            
            if has_shared_chatroom:
                await self.send(text_data=json.dumps({
                    'type' : 'update-online-status',
                    'user_new_status_id' : event['user_new_status_id'],
                    'status' : event['status'],
                }))

    async def force_disconnect(self, event):
        await self.close(code=4001)

    @database_sync_to_async
    def patient_profile_update_last_online(self, patient_profile):
        patient_profile.last_online_at = timezone.now()
        patient_profile.save()

    @database_sync_to_async
    def patient_profile_clear_last_online(self, patient_profile):
        patient_profile.last_online_at = None
        patient_profile.save()

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.user_id = self.user.id
        self.notification_room_name = f'{self.user_id}_notification_room'

        await self.channel_layer.group_add(f"user_{self.user_id}", self.channel_name)
        await self.channel_layer.group_add(self.notification_room_name, self.channel_name)

        await self.accept()

        await self.send(text_data=json.dumps({
            'type' : 'connection',
            'status' : 'connected',
        }))
    
    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.notification_room_name, self.channel_name)
        await self.channel_layer.group_discard(f"user_{self.user_id}", self.channel_name)
    
    async def received_message(self, event):
        
        await self.send(text_data=json.dumps({
            'type' : 'received_message',
            'status' : 'notification + 1',
            'message' : event['message_sended'],
            'message_sender_id' : event['message_sender_id'],
            'user_pfp_url' : event['user_pfp_url'],
            'user_fullname' : event['user_fullname'],
            'user_speciality' : event['user_speciality'],
            'chatroom_name' : event['chatroom_name'],
            'other_user_is_online' : event['other_user_is_online'],
        }))
    
    async def update_new_viewed_messages(self, event):
        
        await self.send(text_data=json.dumps({
            'type' : 'update_new_viewed_messages',
            'messages_ids' : event['messages_ids'][-1],
            'viewer_id' : event['viewer_id'],
        }))
    
    async def force_disconnect(self, event):
        await self.close()