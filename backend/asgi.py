# This file is for Django/Channels - not used with FastAPI
# FastAPI uses uvicorn directly and doesn't need this file
# Keeping for reference only

"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from voice.views import VoiceCallWebSocketConsumer
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agrisarthi.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/voice-stream/", VoiceCallWebSocketConsumer.as_asgi()),
        ])
    ),
})
"""

print("⚠️  ASGI.py: This file is for Django - FastAPI uses uvicorn directly")