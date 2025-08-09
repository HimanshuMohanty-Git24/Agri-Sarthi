import json
import base64
import logging
import asyncio
import audioop
import io
import wave
from typing import Dict, List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Connect, Start
from .services import SarvamAIService, TwilioService, VoiceCallService
from .models import VoiceCallCreate, CallStatus, Speaker

logger = logging.getLogger(__name__)

# Global state management
active_connections: Dict[str, WebSocket] = {}
audio_buffers: Dict[str, List[bytes]] = {}
speech_states: Dict[str, dict] = {}
call_records: Dict[str, str] = {}  # WebSocket ID to Call ID mapping

# Audio processing constants
SILENCE_THRESHOLD = 300
MIN_SPEECH_DURATION_MS = 1500
MAX_SPEECH_DURATION_MS = 15000
SILENCE_DURATION_MS = 1500
SAMPLES_PER_MS = 8

# Initialize services with error handling
try:
    voice_service = VoiceCallService()
    print("✅ VoiceCallService initialized successfully")
except Exception as e:
    print(f"❌ Error initializing VoiceCallService: {e}")
    voice_service = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info(f"WebSocket connected: {connection_id}")

    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        logger.info(f"WebSocket disconnected: {connection_id}")

manager = ConnectionManager()

async def voice_websocket_handler(websocket: WebSocket):
    """Handle voice WebSocket connections"""
    connection_id = f"{websocket.client.host}_{websocket.client.port}_{datetime.now().timestamp()}"
    print(f"🔌 New WebSocket connection attempt: {connection_id}")
    
    try:
        await manager.connect(websocket, connection_id)
        print(f"✅ WebSocket connected successfully: {connection_id}")
        
        # Initialize state for this connection
        audio_buffers[connection_id] = []
        speech_states[connection_id] = {
            'is_speaking': False,
            'speech_start': None,
            'last_speech_time': None,
            'silence_duration': 0
        }
        
        print(f"🎙️ Initializing SarvamAI service...")
        sarvam_service = SarvamAIService()
        print(f"✅ SarvamAI service initialized")
        
        while True:
            try:
                print(f"⏳ Waiting for WebSocket message...")
                data = await websocket.receive_text()
                message = json.loads(data)
                event_type = message.get('event')
                
                print(f"📨 Received event: {event_type}")
                
                if event_type == 'connected':
                    print("🎵 Media stream connected")
                    logger.info("Media stream connected")
                    
                elif event_type == 'start':
                    print("🚀 Call start event received")
                    await handle_call_start(message, connection_id, sarvam_service, websocket)
                    
                elif event_type == 'media':
                    print("🎤 Media chunk received")
                    await handle_media_message(message, connection_id, sarvam_service, websocket)
                    
                elif event_type == 'stop':
                    print("⏹️ Call stop event received")
                    logger.info("Call ended")
                    break
                else:
                    print(f"❓ Unknown event type: {event_type}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                logger.error("Invalid JSON received")
            except Exception as e:
                print(f"❌ Error processing message: {e}")
                logger.error(f"Error processing message: {e}")
                
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: {connection_id}")
        logger.info("WebSocket disconnected")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cleanup
        print(f"🧹 Cleaning up connection: {connection_id}")
        manager.disconnect(connection_id)
        cleanup_connection(connection_id)

async def handle_call_start(message: dict, connection_id: str, sarvam_service: SarvamAIService, websocket: WebSocket):
    """Handle call start event"""
    try:
        if not voice_service:
            logger.error("VoiceCallService not initialized")
            return
            
        start_data = message.get('start', {})
        call_sid = start_data.get('callSid')
        from_number = start_data.get('from', '').replace('+', '')
        
        # Create call record
        call_id = voice_service.create_call_record(
            phone_number=from_number,
            call_sid=call_sid
        )
        call_records[connection_id] = call_id
        
        # Update status to in progress
        voice_service.update_call_status(call_id, CallStatus.IN_PROGRESS)
        
        # Send welcome message
        welcome_msg = "नमस्कार! मैं कृषि सार्थी हूं। मैं आपकी खेती संबंधी सभी समस्याओं में मदद कर सकता हूं। आप क्या जानना चाहते हैं?"
        
        # Save AI welcome message
        voice_service.save_transcript(call_id, Speaker.AI, welcome_msg)
        
        # Convert to audio and send
        await send_audio_response(welcome_msg, websocket, sarvam_service)
        
        logger.info(f"Call started: {call_id}")
        
    except Exception as e:
        logger.error(f"Error handling call start: {e}")

async def handle_media_message(message: dict, connection_id: str, sarvam_service: SarvamAIService, websocket: WebSocket):
    """Handle incoming audio media"""
    try:
        media_data = message.get('media', {})
        payload = media_data.get('payload')
        
        if not payload:
            return
            
        # Decode audio chunk
        audio_chunk = base64.b64decode(payload)
        audio_buffers[connection_id].append(audio_chunk)
        
        # Process speech detection
        await process_speech_detection(audio_chunk, connection_id, sarvam_service, websocket)
        
    except Exception as e:
        logger.error(f"Error handling media message: {e}")

async def process_speech_detection(audio_chunk: bytes, connection_id: str, sarvam_service: SarvamAIService, websocket: WebSocket):
    """Process speech detection and handle complete utterances"""
    try:
        # Calculate RMS for silence detection
        rms = audioop.rms(audio_chunk, 1)
        is_silent = rms < SILENCE_THRESHOLD
        
        current_time = datetime.now()
        state = speech_states[connection_id]
        
        if not is_silent and not state['is_speaking']:
            # Speech started
            state['is_speaking'] = True
            state['speech_start'] = current_time
            state['silence_duration'] = 0
            logger.info("Speech detected - started")
            
        elif is_silent and state['is_speaking']:
            # Potential speech end
            if state['last_speech_time']:
                silence_ms = (current_time - state['last_speech_time']).total_seconds() * 1000
                state['silence_duration'] += silence_ms
                
                # Check if silence duration indicates end of speech
                if state['silence_duration'] >= SILENCE_DURATION_MS:
                    await process_complete_speech(connection_id, sarvam_service, websocket)
                    
        elif not is_silent:
            # Continue speaking
            state['last_speech_time'] = current_time
            state['silence_duration'] = 0
            
    except Exception as e:
        logger.error(f"Error in speech detection: {e}")

async def process_complete_speech(connection_id: str, sarvam_service: SarvamAIService, websocket: WebSocket):
    """Process complete speech utterance"""
    try:
        state = speech_states[connection_id]
        
        if not state['is_speaking']:
            return
            
        # Check minimum speech duration
        if state['speech_start']:
            duration_ms = (datetime.now() - state['speech_start']).total_seconds() * 1000
            if duration_ms < MIN_SPEECH_DURATION_MS:
                logger.info(f"Speech too short: {duration_ms}ms")
                return
        
        # Reset speech state
        state['is_speaking'] = False
        state['speech_start'] = None
        state['silence_duration'] = 0
        
        # Get accumulated audio
        audio_data = b''.join(audio_buffers[connection_id])
        audio_buffers[connection_id] = []  # Clear buffer
        
        if len(audio_data) < 1000:  # Too short
            return
            
        # Convert μ-law to WAV
        wav_audio = convert_mulaw_to_wav(audio_data)
        
        if not wav_audio:
            logger.error("Failed to convert audio to WAV")
            return
            
        # Transcribe audio
        transcript, language = await sarvam_service.transcribe_audio(wav_audio)
        
        if transcript.strip():
            logger.info(f"Farmer said: {transcript}")
            
            # Get call ID
            call_id = call_records.get(connection_id)
            if call_id:
                # Save farmer's message
                voice_service.save_transcript(call_id, Speaker.FARMER, transcript, language)
                
                # Generate AI response
                ai_response = sarvam_service.generate_farmer_response(transcript, language)
                
                # Save AI response
                voice_service.save_transcript(call_id, Speaker.AI, ai_response, language)
                
                # Send audio response
                await send_audio_response(ai_response, websocket, sarvam_service, language)
            
    except Exception as e:
        logger.error(f"Error processing complete speech: {e}")

async def send_audio_response(text: str, websocket: WebSocket, sarvam_service: SarvamAIService, language: str = "hi-IN"):
    """Convert text to speech and send to Twilio"""
    try:
        # Generate TTS audio
        audio_data = await sarvam_service.text_to_speech(text, language)
        
        if not audio_data:
            logger.error("Failed to generate TTS audio")
            return
            
        # Convert to μ-law format for Twilio
        mulaw_audio = convert_wav_to_mulaw(audio_data)
        
        # Send audio in chunks
        await stream_audio_to_twilio(mulaw_audio, websocket)
        
        logger.info(f"Audio response sent: {text[:30]}...")
        
    except Exception as e:
        logger.error(f"Error sending audio response: {e}")

async def stream_audio_to_twilio(audio_data: bytes, websocket: WebSocket, chunk_size: int = 320):
    """Stream audio data to Twilio in chunks"""
    try:
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            
            # Pad chunk if necessary
            if len(chunk) < chunk_size:
                chunk += b'\x00' * (chunk_size - len(chunk))
                
            # Encode and send
            encoded_chunk = base64.b64encode(chunk).decode('utf-8')
            
            message = {
                "event": "media",
                "media": {
                    "payload": encoded_chunk
                }
            }
            
            await websocket.send_text(json.dumps(message))
            await asyncio.sleep(0.02)  # 20ms delay
            
    except Exception as e:
        logger.error(f"Error streaming audio: {e}")

def convert_mulaw_to_wav(mulaw_data: bytes) -> bytes:
    """Convert μ-law to WAV format"""
    try:
        # Convert μ-law to linear PCM
        linear_data = audioop.ulaw2lin(mulaw_data, 1)
        
        # Create WAV file
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(8000)  # 8kHz
            wav_file.writeframes(linear_data)
            
        return wav_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error converting μ-law to WAV: {e}")
        return b''

def convert_wav_to_mulaw(wav_data: bytes) -> bytes:
    """Convert WAV to μ-law format"""
    try:
        wav_buffer = io.BytesIO(wav_data)
        with wave.open(wav_buffer, 'rb') as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())
            sampwidth = wav_file.getsampwidth()
            
        # Convert to μ-law
        mulaw_data = audioop.lin2ulaw(frames, sampwidth)
        return mulaw_data
        
    except Exception as e:
        logger.error(f"Error converting WAV to μ-law: {e}")
        return b''

def cleanup_connection(connection_id: str):
    """Clean up connection data"""
    audio_buffers.pop(connection_id, None)
    speech_states.pop(connection_id, None)
    
    # Update call status to completed
    call_id = call_records.pop(connection_id, None)
    if call_id:
        voice_service.update_call_status(call_id, CallStatus.COMPLETED)

# FastAPI route handlers
def handle_incoming_call():
    """Handle incoming Twilio calls"""
    try:
        response = VoiceResponse()
        
        # Get ngrok URL from environment or construct it
        import os
        ngrok_url = os.getenv("NGROK_URL", "")
        if not ngrok_url:
            raise ValueError("NGROK_URL not set in environment variables")
            
        # Fix WebSocket URL construction - ensure proper format
        if ngrok_url.startswith('https://'):
            ws_domain = ngrok_url.replace('https://', '')
        elif ngrok_url.startswith('http://'):
            ws_domain = ngrok_url.replace('http://', '')
        else:
            ws_domain = ngrok_url
            
        websocket_url = f"wss://{ws_domain}/ws/voice-stream"
        
        print(f"📞 Call received from Twilio")
        print(f"🔗 WebSocket URL: {websocket_url}")
        
        # Create WebSocket connection for media streaming
        connect = Connect()
        start = Start()
        start.stream(url=websocket_url)
        connect.append(start)
        response.append(connect)
        
        # Add a simple Say as fallback
        response.say("कनेक्ट हो रहा है, कृपया प्रतीक्षा करें।", language='hi-IN')
        
        logger.info(f"Incoming call handled, WebSocket URL: {websocket_url}")
        print(f"📋 TwiML Response: {str(response)}")
        
        return Response(content=str(response), media_type="text/xml")
        
    except Exception as e:
        logger.error(f"Error handling incoming call: {e}")
        print(f"❌ Error in handle_incoming_call: {e}")
        response = VoiceResponse()
        response.say("कृपया बाद में कॉल करें। तकनीकी समस्या हो रही है।", language='hi-IN')
        return Response(content=str(response), media_type="text/xml")

def create_outbound_call(call_request: VoiceCallCreate):
    """Create outbound call to farmer"""
    try:
        if not voice_service:
            raise HTTPException(status_code=500, detail="Voice service not initialized")
            
        import os
        twilio_service = TwilioService()
        
        # Get ngrok URL
        ngrok_url = os.getenv("NGROK_URL", "")
        if not ngrok_url:
            raise HTTPException(status_code=500, detail="NGROK_URL not configured")
            
        webhook_url = f"{ngrok_url}/voice/incoming-call"
        
        # Create call
        call_sid = twilio_service.create_outbound_call(
            to_number=call_request.phone_number,
            webhook_url=webhook_url
        )
        
        # Create record
        call_id = voice_service.create_call_record(
            phone_number=call_request.phone_number,
            call_sid=call_sid,
            farmer_name=call_request.farmer_name
        )
        
        return {
            "success": True,
            "call_id": call_id,
            "call_sid": call_sid,
            "message": "Call initiated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating outbound call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_call_history():
    """Get voice call history"""
    try:
        calls = voice_service.get_all_calls()
        return {
            "success": True,
            "calls": calls
        }
    except Exception as e:
        logger.error(f"Error fetching call history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_call_transcript(call_id: str):
    """Get call transcript"""
    try:
        transcript = voice_service.get_call_transcript(call_id)
        return {
            "success": True,
            "call_id": call_id,
            "transcript": transcript
        }
    except Exception as e:
        logger.error(f"Error fetching transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))