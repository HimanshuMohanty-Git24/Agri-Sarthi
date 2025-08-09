# Voice agent URLs are now integrated into main.py FastAPI routes
# This file is kept for reference and potential future modularization

"""
Voice Agent Routes:
- WebSocket: /ws/voice-stream
- POST: /voice/incoming-call (Twilio webhook)
- POST: /voice/outbound-call (Create call)
- GET: /voice/call-history (View calls)
- GET: /voice/call-transcript/{call_id} (Get transcript)
"""