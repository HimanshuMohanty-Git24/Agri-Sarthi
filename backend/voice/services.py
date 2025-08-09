import os
import base64
import json
import logging
import httpx
import tempfile
import wave
import io
import time
import uuid
from typing import Tuple, Optional, Dict, List
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Start
from groq import Groq
from .models import VoiceCallCreate, VoiceCallResponse, TranscriptEntry, CallStatus, Speaker
from datetime import datetime

# In-memory storage (use Redis in production)
voice_calls_db: Dict[str, Dict] = {}
call_transcripts_db: Dict[str, List[Dict]] = {}

logger = logging.getLogger(__name__)

class SarvamAIService:
    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY")
        self.api_url = os.getenv("SARVAM_API_URL", "https://api.sarvam.ai")
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY not found in environment variables")
            
    async def transcribe_audio(self, audio_data: bytes, language: str = "hi-IN") -> Tuple[str, str]:
        """Transcribe audio using Sarvam AI"""
        try:
            # Convert audio to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            payload = {
                "inputs": [audio_base64],
                "model": "sarvam-1",
                "language_code": language,
                "speaker_diarization": False,
                "enable_preprocessing": True
            }
            
            headers = {
                "Content-Type": "application/json",
                "API-Subscription-Key": self.api_key
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/speech-to-text",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    transcript = result.get("transcript", "")
                    detected_language = result.get("language_code", language)
                    logger.info(f"Transcription successful: {transcript[:50]}...")
                    return transcript, detected_language
                else:
                    logger.error(f"Sarvam transcription failed: {response.status_code} - {response.text}")
                    return "", language
                    
        except Exception as e:
            logger.error(f"Error in transcribe_audio: {e}")
            return "", language

    def generate_farmer_response(self, user_message: str, language: str = "hi-IN", farmer_context: dict = None) -> str:
        """Generate contextual response for farmers using Groq"""
        try:
            # Enhanced farmer-specific system prompt in Hindi/English
            if language.startswith("hi"):
                system_prompt = f"""आप एक विशेषज्ञ कृषि सलाहकार हैं जो भारतीय किसानों की मदद करते हैं। 
                आपका नाम "कृषि सार्थी" है और आप निम्नलिखित क्षेत्रों में सहायता प्रदान करते हैं:

                🌾 फसल की जानकारी और सलाह
                🌡️ मौसम की जानकारी और चेतावनी
                💰 बाजार भाव और कीमतें
                🚜 सरकारी योजनाएं और सब्सिडी (PM-KUSUM, electricity subsidies)
                🐛 कीट और रोग प्रबंधन
                🌱 बीज और खाद की जानकारी
                💧 सिंचाई तकनीक
                📊 आधुनिक कृषि तकनीक

                महत्वपूर्ण निर्देश:
                - हमेशा सरल हिंदी में उत्तर दें
                - व्यावहारिक सुझाव दें जो किसान तुरंत लागू कर सके
                - 2-3 वाक्यों में संक्षिप्त उत्तर दें
                - यदि पूरी जानकारी नहीं है तो स्थानीय कृषि अधिकारी से संपर्क करने को कहें
                """
            else:
                system_prompt = f"""You are an expert agricultural advisor helping Indian farmers.
                Your name is "Krishi Sarthi" and you provide assistance in:

                🌾 Crop information and advice
                🌡️ Weather information and alerts
                💰 Market prices and rates
                🚜 Government schemes and subsidies
                🐛 Pest and disease management
                🌱 Seeds and fertilizer information
                💧 Irrigation techniques
                📊 Modern farming technology

                Important instructions:
                - Always respond in simple, understandable language
                - Provide practical, actionable advice
                - Keep responses to 2-3 sentences
                - If you don't have complete information, advise consulting local agricultural officers
                """
            
            # Add farmer context if available
            if farmer_context:
                system_prompt += f"\nकिसान की जानकारी: {farmer_context}"

            response = self.groq_client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"Generated response: {ai_response[:50]}...")
            return ai_response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "क्षमा करें, मुझे कुछ तकनीकी समस्या हो रही है। कृपया दोबारा प्रयास करें।"

    async def text_to_speech(self, text: str, language: str = "hi-IN") -> Optional[bytes]:
        """Convert text to speech using Sarvam AI"""
        try:
            payload = {
                "inputs": [text],
                "target_language_code": language,
                "speaker": "meera",  # Female voice suitable for Indian context
                "pitch": 0,
                "pace": 1.0,
                "loudness": 1.5,
                "speech_sample_rate": 8000,
                "enable_preprocessing": True,
                "model": "bulbul:v1"
            }
            
            headers = {
                "Content-Type": "application/json", 
                "API-Subscription-Key": self.api_key
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url}/text-to-speech",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    audio_base64 = result.get("audios", [None])[0]
                    if audio_base64:
                        logger.info("TTS conversion successful")
                        return base64.b64decode(audio_base64)
                else:
                    logger.error(f"TTS failed: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Error in text_to_speech: {e}")
            
        return None

class TwilioService:
    def __init__(self):
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        if not account_sid or not auth_token:
            raise ValueError("Twilio credentials not found in environment variables")
            
        self.client = Client(account_sid, auth_token)
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        
    def create_outbound_call(self, to_number: str, webhook_url: str) -> str:
        """Create an outbound call"""
        try:
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                url=webhook_url,
                method='POST'
            )
            logger.info(f"Outbound call created: {call.sid}")
            return call.sid
        except Exception as e:
            logger.error(f"Error creating outbound call: {e}")
            raise

class VoiceCallService:
    def __init__(self):
        self.sarvam_service = SarvamAIService()
        self.twilio_service = TwilioService()
    
    def create_call_record(self, phone_number: str, call_sid: str, farmer_name: str = None) -> str:
        """Create a voice call record"""
        call_id = str(uuid.uuid4())
        
        call_data = {
            "id": call_id,
            "phone_number": phone_number,
            "call_sid": call_sid,
            "status": CallStatus.INITIATED,
            "farmer_name": farmer_name,
            "created_at": datetime.now(),
            "duration": None,
            "conversation_summary": ""
        }
        
        voice_calls_db[call_id] = call_data
        call_transcripts_db[call_id] = []
        
        logger.info(f"Call record created: {call_id}")
        return call_id
    
    def get_call_by_sid(self, call_sid: str) -> Optional[Dict]:
        """Get call record by Twilio SID"""
        for call_data in voice_calls_db.values():
            if call_data.get("call_sid") == call_sid:
                return call_data
        return None
    
    def update_call_status(self, call_id: str, status: CallStatus, **kwargs):
        """Update call status"""
        if call_id in voice_calls_db:
            voice_calls_db[call_id]["status"] = status
            for key, value in kwargs.items():
                voice_calls_db[call_id][key] = value
            logger.info(f"Call {call_id} status updated to {status}")
    
    def save_transcript(self, call_id: str, speaker: Speaker, message: str, language: str = "hi-IN"):
        """Save conversation transcript"""
        if call_id not in call_transcripts_db:
            call_transcripts_db[call_id] = []
            
        transcript_entry = {
            "speaker": speaker,
            "message": message,
            "language": language,
            "timestamp": datetime.now()
        }
        
        call_transcripts_db[call_id].append(transcript_entry)
        logger.info(f"Transcript saved for call {call_id}: {speaker} - {message[:30]}...")
    
    def get_all_calls(self) -> List[Dict]:
        """Get all call records"""
        return list(voice_calls_db.values())
    
    def get_call_transcript(self, call_id: str) -> List[Dict]:
        """Get call transcript"""
        return call_transcripts_db.get(call_id, [])