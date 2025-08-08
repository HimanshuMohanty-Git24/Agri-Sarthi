import os
from dotenv import load_dotenv

# --- CRITICAL FIX ---
# Load environment variables from .env file BEFORE any other imports
# that might need them.
load_dotenv()
print("--- .env file loaded ---")
print(f"Environment file load result: {load_dotenv()}")
print(f"TAVILY_API_KEY loaded: {'Yes' if os.getenv('TAVILY_API_KEY') else 'No'}")
print(f"GOOGLE_API_KEY loaded: {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")
print(f"GROQ_API_KEY loaded: {'Yes' if os.getenv('GROQ_API_KEY') else 'No'}")
if not os.getenv('GROQ_API_KEY'):
    print("ERROR: Required API keys are missing!")
    exit(1)
# --------------------

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
print("Basic imports successful")

try:
    print("Attempting to import agent...")
    from agent import agentic_workflow
    print("Agent import successful")
except Exception as e:
    print(f"Agent import failed: {e}")
    print("Creating dummy agent for testing...")
    
    # Create a dummy agent that just echoes
    class DummyAgent:
        def astream_events(self, input_data, config, version):
            async def dummy_generator():
                yield {
                    "event": "on_chat_model_stream",
                    "data": {"chunk": type('obj', (object,), {"content": f"Echo: {input_data['messages'][0].content}"})()}
                }
            return dummy_generator()
    
    agentic_workflow = DummyAgent()

from fastapi.responses import StreamingResponse
import json
print("All imports completed successfully")

# Initialize FastAPI app
app = FastAPI()
print("FastAPI app initialized")

# Configure CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("CORS middleware configured")

# Define the request model for the chat endpoint
class ChatRequest(BaseModel):
    message: str
    thread_id: str

# --- Streaming Response Generator ---
async def stream_generator(thread_id: str, user_message: str):
    config = {"configurable": {"thread_id": thread_id}}
    input_message = [HumanMessage(content=user_message)]
    
    print(f"🔄 Starting stream for query: {user_message}")
    
    # Collect all content first, then clean and stream
    full_response = ""
    tool_events = []
    
    try:
        # First pass: collect all content
        async for event in agentic_workflow.astream_events(
            {"messages": input_message}, config, version="v2"
        ):
            try:
                kind = event.get("event", "")
                print(f"📊 Event received: {kind}")
                
                if kind == "on_chat_model_stream":
                    # Safely get content
                    data = event.get("data", {})
                    chunk = data.get("chunk", {})
                    
                    if hasattr(chunk, 'content'):
                        content = chunk.content
                    elif isinstance(chunk, dict) and 'content' in chunk:
                        content = chunk['content']
                    elif isinstance(chunk, str):
                        content = chunk
                    else:
                        content = str(chunk) if chunk else ""
                    
                    if content:
                        full_response += content
                        print(f"📝 Accumulated content: {len(full_response)} chars")
                
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    tool_input = event.get('data', {}).get('input', {})
                    print(f"Tool started: {tool_name} with input: {tool_input}")
                    tool_events.append({"type": "start", "name": tool_name, "input": tool_input})
                
                elif kind == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    tool_output = event.get("data", {}).get("output", "")
                    print(f"Tool completed: {tool_name}")
                    
                    # Safely convert tool output to string
                    try:
                        if hasattr(tool_output, 'content'):
                            output_str = str(tool_output.content)
                        elif isinstance(tool_output, str):
                            output_str = tool_output
                        else:
                            output_str = str(tool_output)
                    except Exception as e:
                        output_str = f"Error processing tool output: {str(e)}"
                    
                    print(f"Tool output preview: {output_str[:200]}...")
                    tool_events.append({"type": "end", "name": tool_name, "output": output_str})
                    
            except Exception as inner_e:
                print(f"ERROR: Error processing event: {inner_e}")
                print(f"Event that caused error: {event}")
                # Don't break, continue processing
                continue
        
        print(f"Processing final response. Raw length: {len(full_response)}")
        
        # Second pass: clean the full response and stream it properly
        if full_response:
            import re
            
            # Light cleaning - only remove agent names at the beginning
            cleaned_response = full_response.strip()
            print(f"Original response starts with: {cleaned_response[:50]}...")
            
            # Only remove agent names if they appear at the very start
            agent_names = ['MarketAnalyst', 'SoilCropAdvisor', 'FinancialAdvisor', 'Supervisor', 'WeatherAgent']
            for name in agent_names:
                if cleaned_response.startswith(name):
                    cleaned_response = re.sub(f'^{re.escape(name)}[:\s]*', '', cleaned_response).strip()
                    print(f"Removed agent name: {name}")
                    break
            
            # Make sure it starts properly
            if cleaned_response and not cleaned_response[0].isupper():
                cleaned_response = cleaned_response[0].upper() + cleaned_response[1:] if len(cleaned_response) > 1 else cleaned_response.upper()
            
            print(f"Final cleaned response starts with: {cleaned_response[:50]}...")
            
            # Stream tool events first (hidden from user but logged)
            for event in tool_events:
                if event["type"] == "start":
                    print(f"Tool starting: {event['name']}")
                    yield f"data: {json.dumps({'tool_start': event['name'], 'tool_input': event.get('input')})}\n\n"
                elif event["type"] == "end":
                    print(f"Tool completed: {event['name']}")
                    yield f"data: {json.dumps({'tool_end': event['name'], 'tool_output': event['output']})}\n\n"
            
            # Stream the cleaned response character by character for proper formatting
            if cleaned_response:
                for char in cleaned_response:
                    yield f"data: {json.dumps({'content': char})}\n\n"
                    
                    # Small delay for natural feel (every few characters)
                    import asyncio
                    await asyncio.sleep(0.02)  # Reduced delay for smoother streaming
            else:
                # Fallback response if cleaning removed everything
                print("WARNING: Cleaned response is empty, using fallback")
                fallback_msg = "I apologize, but I couldn't process that request properly. Please try again."
                for char in fallback_msg:
                    yield f"data: {json.dumps({'content': char})}\n\n"
        else:
            # No response collected, send error
            print("ERROR: No response collected from agent")
            error_msg = "I'm having trouble getting information right now. Please try again."
            for char in error_msg:
                yield f"data: {json.dumps({'content': char})}\n\n"
        
    except Exception as e:
        print(f"ERROR: Major error in stream_generator: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        # Emergency fallback - provide a simple response
        fallback_msg = "I'm experiencing technical difficulties. Please try asking your question again, or contact support if the issue persists."
        
        for char in fallback_msg:
            yield f"data: {json.dumps({'content': char})}\n\n"

# --- API Endpoint ---
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    print(f"Received chat request: {request.message[:50]}...")
    return StreamingResponse(
        stream_generator(request.thread_id, request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Add OPTIONS endpoint for CORS preflight
@app.options("/chat")
async def chat_options():
    return {"message": "OK"}

# --- Root Endpoint for Health Check ---
@app.get("/")
def read_root():
    print("Root endpoint accessed")
    return {"status": "Agri Sarthi backend is running"}

# Test endpoint
@app.get("/test")
def test_endpoint():
    print("Test endpoint accessed")
    return {"message": "Backend is working!"}

# Add startup event
@app.on_event("startup")
async def startup_event():
    print("=== BACKEND STARTUP ===")
    print("Backend is starting up...")
    print("Server should be accessible on http://localhost:8000")
    print("Test endpoint: http://localhost:8000/test")
    print("Chat endpoint: http://localhost:8000/chat")
    print("======================")

# To run this server, use the command: uvicorn main:app --reload --host 0.0.0.0
