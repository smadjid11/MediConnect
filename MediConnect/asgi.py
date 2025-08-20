"""
ASGI config for MediConnect project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import django

django.setup()

from django.core.asgi import get_asgi_application
from channels.security.websocket import AllowedHostsOriginValidator
from channels.routing import URLRouter, ProtocolTypeRouter
from channels.auth import AuthMiddlewareStack
from chat import routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MediConnect.settings')

application = ProtocolTypeRouter({
    'http' : get_asgi_application(),
    'websocket' : AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(routing.websocket_patterns)
        )
    )
})