from django.urls import path
from . import views

urlpatterns = [
    path('messages', views.messages, name='messages'),
    path('start-chat/<str:username>', views.start_chat, name='start-chat'),
    path('<str:chatroom_name>', views.chat, name='chat'),
    path('protected/messages/<int:message_id>', views.protected_message_image, name='protected-message-image'),
]
