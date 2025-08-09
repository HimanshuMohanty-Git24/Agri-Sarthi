import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()
print("--- .env file loaded ---")
print(f"Environment file load result: {load_dotenv()}")
print(f"TAVILY_API_KEY loaded: {'Yes' if os.getenv('TAVILY_API_KEY') else 'No'}")
print(f"GOOGLE_API_KEY loaded: {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")
print(f"GROQ_API_KEY loaded: {'Yes' if os.getenv('GROQ_API_KEY') else 'No'}")
print(f"SARVAM_API_KEY loaded: {'Yes' if os.getenv('SARVAM_API_KEY') else 'No'}")
print(f"TWILIO_ACCOUNT_SID loaded: {'Yes' if os.getenv('TWILIO_ACCOUNT_SID') else 'No'}")

if not os.getenv('GROQ_API_KEY'):
    exit(1)

from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from fastapi.responses import StreamingResponse
import json

print("Basic imports successful")

# Import voice-related modules
voice_routes_enabled = False
VoiceCallCreate = None
handle_incoming_call = None
create_outbound_call = None
get_call_history = None
get_call_transcript = None
voice_websocket_handler = None

try:
    from voice.views import (
        voice_websocket_handler, 
        handle_incoming_call, 
        create_outbound_call, 
        get_call_history,
        get_call_transcript
    )
    from voice.models import VoiceCallCreate
    voice_routes_enabled = True
    print("✅ Voice agent imports successful")
except Exception as e:
    print(f"❌ Voice agent import error: {e}")
    print("📱 Voice routes will be disabled")

try:
    from agent import agentic_workflow
    print("✅ Agent import successful")
except Exception as e:
    print(f"❌ Agent import error: {e}")

print("All imports completed successfully")

# Initialize FastAPI app
app = FastAPI(title="Agri Sarthi - Smart Farming Assistant", version="1.0.0")
print("FastAPI app initialized")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("CORS middleware configured")

# Define the request model for the chat endpoint
class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"

# Debug: Add a simple test route immediately
@app.get("/debug/test")
async def debug_test():
    return {"message": "Debug route works", "voice_enabled": voice_routes_enabled}

@app.get("/debug/routes")
async def debug_routes():
    """Debug endpoint to list all routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = getattr(route, 'methods', set())
            if methods:
                routes.append({"path": route.path, "methods": list(methods)})
    return {"total_routes": len(routes), "routes": routes}

print("🧪 Debug routes added")

# Debug: Show variable status
print(f"🔍 Debug - voice_routes_enabled: {voice_routes_enabled}")
if voice_routes_enabled:
    print(f"🔍 Debug - VoiceCallCreate available: {VoiceCallCreate}")
    print(f"🔍 Debug - handle_incoming_call available: {callable(handle_incoming_call)}")

# --- VOICE AGENT ROUTES ---

@app.get("/voice/test")
async def voice_test_endpoint():
    """Test voice endpoint"""
    import os
    ngrok_url = os.getenv("NGROK_URL", "Not set")
    
    # Generate the WebSocket URL that would be used
    if ngrok_url.startswith('https://'):
        ws_domain = ngrok_url.replace('https://', '')
    elif ngrok_url.startswith('http://'):
        ws_domain = ngrok_url.replace('http://', '')
    else:
        ws_domain = ngrok_url
    
    websocket_url = f"wss://{ws_domain}/ws/voice-stream"
    
    return {
        "message": "Voice agent endpoint accessible!", 
        "status": "success",
        "voice_enabled": voice_routes_enabled,
        "ngrok_url": ngrok_url,
        "websocket_url": websocket_url,
        "websocket_route_registered": "/ws/voice-stream"
    }

@app.get("/voice/test-websocket")
async def test_websocket_endpoint():
    """Test WebSocket URL generation"""
    import os
    ngrok_url = os.getenv("NGROK_URL", "Not set")
    
    if ngrok_url.startswith('https://'):
        ws_domain = ngrok_url.replace('https://', '')
    elif ngrok_url.startswith('http://'):
        ws_domain = ngrok_url.replace('http://', '')
    else:
        ws_domain = ngrok_url
    
    websocket_url = f"wss://{ws_domain}/ws/voice-stream"
    
    # Create a test TwiML response to see what Twilio would receive
    test_twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Start>
            <Stream url="{websocket_url}" />
        </Start>
    </Connect>
    <Say language="hi-IN">कनेक्ट हो रहा है, कृपया प्रतीक्षा करें।</Say>
</Response>"""
    
    return {
        "websocket_url": websocket_url,
        "ngrok_url": ngrok_url,
        "test_twiml": test_twiml
    }

# Define voice routes regardless of import status, but handle errors gracefully
@app.websocket("/ws/voice-stream")
async def voice_websocket_endpoint(websocket):
    """WebSocket endpoint for voice streaming"""
    print(f"🔌 WebSocket connection attempt from {websocket.client}")
    print(f"🔗 WebSocket headers: {dict(websocket.headers)}")
    print(f"🎯 WebSocket path: {websocket.url.path}")
    
    if not voice_routes_enabled:
        print("❌ Voice service unavailable - closing WebSocket")
        await websocket.close(code=1000, reason="Voice service unavailable")
        return
    try:
        print("✅ Voice service available - handling WebSocket")
        await voice_websocket_handler(websocket)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass

@app.websocket("/ws/test")
async def test_websocket(websocket):
    """Simple WebSocket test endpoint"""
    print(f"🧪 Test WebSocket connection attempt from {websocket.client}")
    await websocket.accept()
    print(f"✅ Test WebSocket connected successfully")
    
    try:
        await websocket.send_text("Hello from WebSocket!")
        print(f"� Test message sent")
        
        # Wait for a response or timeout
        data = await websocket.receive_text()
        print(f"📥 Received: {data}")
        
        await websocket.send_text("Echo: " + data)
        await websocket.close()
        
    except Exception as e:
        print(f"❌ Test WebSocket error: {e}")

print("🧪 Test WebSocket route added")

@app.post("/voice/incoming-call", status_code=200)
async def incoming_call_endpoint():
    """Handle incoming Twilio voice calls"""
    print("📞 Incoming call received")
    
    if not voice_routes_enabled:
        from fastapi.responses import Response
        return Response(
            content="<Response><Say>Voice agent is currently unavailable. Please try again later.</Say></Response>", 
            media_type="text/xml"
        )
    
    try:
        return handle_incoming_call()
    except Exception as e:
        print(f"Error handling incoming call: {e}")
        from fastapi.responses import Response
        return Response(content="<Response><Say>Technical error occurred</Say></Response>", media_type="text/xml")

print("🔧 Voice incoming call route added")

@app.post("/voice/outbound-call")
async def outbound_call_endpoint(call_request: dict):
    """Create outbound call to farmer"""
    if not voice_routes_enabled:
        return {"error": "Voice service not available"}
    
    # Convert dict to VoiceCallCreate if voice is enabled
    try:
        if voice_routes_enabled and VoiceCallCreate:
            call_obj = VoiceCallCreate(**call_request)
            print(f"📞 Creating outbound call to {call_obj.phone_number}")
            return create_outbound_call(call_obj)
        else:
            return {"error": "Voice models not available"}
    except Exception as e:
        print(f"Error creating outbound call: {e}")
        return {"error": str(e)}

print("🔧 Voice outbound call route added")

@app.get("/voice/call-history")
async def call_history_endpoint():
    """Get voice call history"""
    if not voice_routes_enabled:
        return {"error": "Voice service not available", "calls": []}
    
    print("📋 Fetching call history")
    try:
        return get_call_history()
    except Exception as e:
        print(f"Error fetching call history: {e}")
        return {"error": str(e)}

print("🔧 Voice call history route added")

@app.get("/voice/call-transcript/{call_id}")
async def call_transcript_endpoint(call_id: str):
    """Get call transcript"""
    if not voice_routes_enabled:
        return {"error": "Voice service not available", "transcript": []}
    
    print(f"📋 Fetching transcript for call {call_id}")
    try:
        return get_call_transcript(call_id)
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return {"error": str(e)}

print("🔧 Voice call transcript route added")

# --- EXISTING CHAT ROUTES ---

async def stream_generator(thread_id: str, user_message: str):
    """Generate streaming response for chat"""
    try:
        config = {"configurable": {"thread_id": thread_id}}
        
        async for event in agentic_workflow.astream_events(
            {"messages": [HumanMessage(content=user_message)]}, 
            config, 
            version="v1"
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield f"data: {json.dumps({'content': content})}\n\n"
        
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
        
    except Exception as e:
        print(f"Error in stream_generator: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint with streaming response"""
    try:
        return StreamingResponse(
            stream_generator(request.thread_id, request.message),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return {"error": str(e)}

@app.options("/chat")
async def chat_options():
    """Handle CORS preflight for chat"""
    return {"message": "OK"}

# --- HEALTH CHECK ROUTES ---

@app.get("/")
def read_root():
    """Root endpoint for health check"""
    return {
        "message": "🌾 Agri Sarthi - Smart Farming Assistant API", 
        "status": "Active",
        "version": "1.0.0",
        "features": ["Chat AI", "Voice Agent", "Market Data", "Weather Alerts"]
    }

@app.get("/test")
def test_endpoint():
    """Test endpoint"""
    return {"message": "Test successful", "timestamp": "2024"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "voice_agent": "enabled",
        "chat_agent": "enabled"
    }

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    print("\n" + "="*50)
    print("🚀 Agri Sarthi application started successfully!")
    print("✅ Chat Agent: Ready")
    
    if voice_routes_enabled:
        print("✅ Voice Agent: Ready") 
        print("📞 Voice WebSocket: /ws/voice-stream")
        print("🗣️  Twilio Webhook: /voice/incoming-call")
        print("📋 Call History: /voice/call-history")
        print("🧪 Voice Test: /voice/test")
    else:
        print("❌ Voice Agent: Disabled (Import errors)")
        print("🗣️  Twilio Webhook: /voice/incoming-call (fallback)")
    
    print(f"🌐 NGROK URL: {os.getenv('NGROK_URL', 'Not configured')}")
    print("📚 API Docs: http://localhost:8000/docs")
    
    # List all registered routes for debugging
    print("\n📋 Registered Routes:")
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = getattr(route, 'methods', set())
            if methods and route.path not in ['/openapi.json', '/docs', '/redoc']:  # Skip auto-generated routes
                print(f"   {methods} {route.path}")
    print("="*50)

print("🎯 All routes and startup configured!")

# Final check - add a simple voice route at the very end to test registration
@app.get("/voice-simple-test")
async def voice_simple_test():
    return {"message": "Simple voice test works", "timestamp": "2024"}

print("🔧 Simple voice test route added at the end")

# To run: uvicorn main:app --reload --host 0.0.0.0 --port 8000
