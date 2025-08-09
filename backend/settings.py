import os
# Add to INSTALLED_APPS
INSTALLED_APPS = [
    # ... existing apps
    'agrisarthi.voice',
    'channels',  # For WebSocket support
]

# Voice Agent Settings
SARVAM_API_KEY = os.getenv('SARVAM_API_KEY', '')
SARVAM_API_URL = os.getenv('SARVAM_API_URL', 'https://api.sarvam.ai')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')

# Twilio Settings
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

# WebSocket/Channels configuration
ASGI_APPLICATION = 'agrisarthi.asgi.application'

# Channel layers for WebSocket
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'voice_agent.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'agrisarthi.voice': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}