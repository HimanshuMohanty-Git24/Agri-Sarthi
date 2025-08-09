#!/usr/bin/env python3
"""Test script to check voice agent dependencies"""

import os
from dotenv import load_dotenv

def test_dependencies():
    """Test all voice agent dependencies"""
    print("🧪 Testing Voice Agent Dependencies...")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    print("✅ Environment variables loaded")
    
    # Test environment variables
    required_vars = [
        "GROQ_API_KEY",
        "SARVAM_API_KEY", 
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER",
        "NGROK_URL"
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        status = "✅" if value else "❌"
        print(f"{status} {var}: {'Set' if value else 'Missing'}")
    
    # Test imports
    print("\n📦 Testing Imports...")
    print("-" * 30)
    
    try:
        import twilio
        print("✅ Twilio imported successfully")
    except ImportError as e:
        print(f"❌ Twilio import failed: {e}")
    
    try:
        import groq
        print("✅ Groq imported successfully")
    except ImportError as e:
        print(f"❌ Groq import failed: {e}")
    
    try:
        import httpx
        print("✅ HTTPX imported successfully")
    except ImportError as e:
        print(f"❌ HTTPX import failed: {e}")
    
    try:
        import audioop
        print("✅ Audioop imported successfully")
    except ImportError as e:
        print(f"❌ Audioop import failed: {e}")
    
    # Test voice module imports
    print("\n🎙️ Testing Voice Module Imports...")
    print("-" * 40)
    
    try:
        from voice.models import VoiceCallCreate, CallStatus, Speaker
        print("✅ Voice models imported successfully")
    except ImportError as e:
        print(f"❌ Voice models import failed: {e}")
    
    try:
        from voice.services import SarvamAIService, TwilioService, VoiceCallService
        print("✅ Voice services imported successfully")
    except ImportError as e:
        print(f"❌ Voice services import failed: {e}")
    
    try:
        from voice.views import handle_incoming_call
        print("✅ Voice views imported successfully")
    except ImportError as e:
        print(f"❌ Voice views import failed: {e}")
    
    # Test service initialization
    print("\n🔧 Testing Service Initialization...")
    print("-" * 40)
    
    try:
        from voice.services import SarvamAIService
        sarvam = SarvamAIService()
        print("✅ SarvamAIService initialized successfully")
    except Exception as e:
        print(f"❌ SarvamAIService initialization failed: {e}")
    
    try:
        from voice.services import TwilioService
        twilio_svc = TwilioService()
        print("✅ TwilioService initialized successfully")
    except Exception as e:
        print(f"❌ TwilioService initialization failed: {e}")
    
    try:
        from voice.services import VoiceCallService
        voice_svc = VoiceCallService()
        print("✅ VoiceCallService initialized successfully")
    except Exception as e:
        print(f"❌ VoiceCallService initialization failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Test completed! Check results above.")

if __name__ == "__main__":
    test_dependencies()