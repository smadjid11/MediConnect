from django.urls import path
from .consumers import ChatConsumer, OnlineStatusConsumer, NotificationConsumer

websocket_patterns = [
    path('ws/chatroom/<chatroom_name>', ChatConsumer.as_asgi()),
    path('ws/online_status', OnlineStatusConsumer.as_asgi()),
    path('ws/notification', NotificationConsumer.as_asgi()),
]