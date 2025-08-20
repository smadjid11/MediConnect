from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import *
from django.http import Http404
from django.contrib import messages as msgs
from django.db.models import Max
import redis
from django.http import JsonResponse, FileResponse
import mimetypes
from django.conf import settings
import os

def delete_chatroom(chatroom_deleted):
    for message in chatroom_deleted.messages.all():
        if message.image:
            os.remove(message.image.path)
    chatroom_deleted.delete()

@login_required
def messages(request):
    chatrooms = ChatRoom.objects.filter(members=request.user).annotate(last_message_time=Max('messages__created')).order_by('-last_message_time')
    r = redis.Redis.from_url(settings.URL_REDIS_DB_1, decode_responses=True)

    # context_nedeeded = [[chatroom, last_message, other_user, other_user_is_online], ....]
    chatrooms_list = []

    for chatroom in chatrooms:
        # For Check If There Is Messages
        there_is_messages = True
        deletion_info = ChatRoomDelete.objects.filter(chatroom = chatroom, user = request.user).first()
        if deletion_info:
            messages = chatroom.messages.filter(created__gt = deletion_info.deleted_at)
            if not messages:
                there_is_messages = False

        if there_is_messages:
            new_list = []
            new_list.append(chatroom)
            last_message = chatroom.messages.last()
            new_list.append(last_message)
            other_user = chatroom.members.exclude(username = request.user.username).first()
            new_list.append(other_user)
            # ِCheck If Other User Is Online Or No
            if other_user:
                other_user_is_online = False
                remaining = r.hget('online_room_users', other_user.id)
                if remaining and int(remaining) >= 1:
                    other_user_is_online = True
                new_list.append(other_user_is_online)
            else:
                new_list.append(None)
            
            chatrooms_list.append(new_list)

    context = {
        'chatrooms' : chatrooms_list,
    }
    return render(request, 'chat/messages.html', context)

def start_chat(request, username):
    if request.user.is_anonymous:
        msgs.error(request, 'you must login first !')
        return redirect('login')
    
    other_user = get_object_or_404(User, username=username)
    if request.user == other_user:
        raise Http404()
    # if not hasattr(other_user, 'doctorprofile'):
    #     raise Http404()
    
    chatroom = ChatRoom.objects.filter(members = request.user).filter(members = other_user).first()
    if not chatroom:
        chatroom = ChatRoom.objects.create()
        chatroom.members.add(request.user, other_user)

    return redirect('chat', chatroom.chatroom_name)

@login_required
def chat(request, chatroom_name):
    # For Select ChatRoom
    chatroom = get_object_or_404(ChatRoom, chatroom_name=chatroom_name)
    # For Check If User Is Member In Chat Room
    if request.user not in chatroom.members.all():
        raise Http404()
    
    # Select Other User
    other_user = chatroom.members.exclude(id = request.user.id).first()
    other_profile = None
    other_user_is_online = None
    if other_user:
        other_profile = None
        if hasattr(other_user, 'patientprofile'):
            other_profile = other_user.patientprofile
        elif hasattr(other_user, 'doctorprofile'):
            other_profile = other_user.doctorprofile
        elif hasattr(other_user, 'adminprofile'):
            other_profile = other_user.adminprofile
        # ِCheck If Other User Is Online Or No
        r = redis.Redis.from_url(settings.URL_REDIS_DB_1, decode_responses=True)
        other_user_is_online = False
        remaining = r.hget('online_room_users', other_user.id)
        if remaining and int(remaining) >= 1:
            other_user_is_online = True
    
    if request.method == 'POST':
        chatroom_deleted = False
        if chatroom.members.count() <= 1:
            
            delete_chatroom(chatroom)
            chatroom_deleted = True
        
        if not chatroom_deleted:
            # For Add User To deleted_from field
            chatroom.mark_delete_for(request.user)
            # If Chatroom Has Already No Messages
            if chatroom.messages.count() == 0:
                delete_chatroom(chatroom)
                chatroom_deleted = True
        
        if not chatroom_deleted:
            # If the two users already delete all conversation
            all_messages_chatroom = chatroom.messages.all()
            messages1 = None
            messages2 = None
            deletion_info1 = ChatRoomDelete.objects.filter(chatroom = chatroom, user = request.user).first()
            if deletion_info1:
                messages1 = chatroom.messages.filter(created__gt = deletion_info1.deleted_at)
            else:
                messages1 = all_messages_chatroom
            deletion_info2 = ChatRoomDelete.objects.filter(chatroom = chatroom, user = other_user).first()
            if deletion_info2:
                messages2 = chatroom.messages.filter(created__gt = deletion_info2.deleted_at)
            else:
                messages2 = all_messages_chatroom
            if not messages1.exists() and not messages2.exists():
                delete_chatroom(chatroom)
                chatroom_deleted = True
            if not chatroom_deleted and deletion_info1 and deletion_info2:
                # For Delete The Same Messages Deleted From Two Users
                messages1 = chatroom.messages.filter(created__lt = deletion_info1.deleted_at)
                messages2 = chatroom.messages.filter(created__lt = deletion_info2.deleted_at)
                if messages1.exists() and messages2.exists():
                    deleted_messages = messages1 & messages2
                    deleted_messages.delete()

        return redirect('messages')

    # For Make Last Messages Is Viewed If There's No Other User
    last_message = chatroom.messages.last()
    if not other_user and last_message:
        if not last_message.is_viewed:
            last_message.is_viewed = True
            last_message.save()
    # Check Deleted Messages For User
    deletion_info = ChatRoomDelete.objects.filter(chatroom=chatroom, user=request.user).first()
    if deletion_info:
        messages = chatroom.messages.filter(created__gt = deletion_info.deleted_at)
    else:
        messages = chatroom.messages.all()

    context = {
        'chatroom' : chatroom,
        'other_user' : other_user,
        'other_profile' : other_profile,
        'messages' : messages,
        'other_user_is_online' : other_user_is_online,
    }
    return render(request, 'chat/chat.html', context)

@login_required
def protected_message_image(request, message_id):
    try:
        message = ChatMessage.objects.get(id=message_id)
    except ChatMessage.DoesNotExist:
        raise Http404()
    
    chatroom = message.chatroom
    
    if request.user in chatroom.members.all():
        if message.image:
            file_path = message.image.path
            content_type, _ = mimetypes.guess_type(file_path)
            return FileResponse(open(file_path, 'rb'), content_type=content_type)
        else:
            raise Http404()
    else:
        raise Http404()