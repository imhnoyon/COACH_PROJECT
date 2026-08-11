"""
ASGI config for COACH_PROJECT project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'COACH_PROJECT.settings')

# Initialize Django ASGI application early to ensure the AppRegistry is populated before importing models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from Message.middleware import JWTAuthMiddlewareStack
import Message.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(
                Message.routing.websocket_urlpatterns
            )
        )
    ),
})

