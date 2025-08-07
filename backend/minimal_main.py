import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()
print("--- .env file loaded ---")
print(f"TAVILY_API_KEY loaded: {'Yes' if os.getenv('TAVILY_API_KEY') else 'No'}")
print(f"GOOGLE_API_KEY loaded: {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")
print(f"GROQ_API_KEY loaded: {'Yes' if os.getenv('GROQ_API_KEY') else 'No'}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from fastapi.responses import StreamingResponse
import json

# Initialize FastAPI app
app = FastAPI()
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

# Request model
class ChatRequest(BaseModel):
    message: str
    thread_id: str

# Simple streaming response for testing
async def simple_stream_generator(user_message: str):
    """Simple streaming response without agent"""
    response_text = f"Echo: {user_message}"
    for char in response_text:
        yield f"data: {json.dumps({'content': char})}\n\n"
        import asyncio
        await asyncio.sleep(0.05)  # Small delay to simulate streaming

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    print(f"Received chat request: {request.message[:50]}...")
    return StreamingResponse(
        simple_stream_generator(request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.options("/chat")
async def chat_options():
    return {"message": "OK"}

@app.get("/")
def read_root():
    print("Root endpoint accessed")
    return {"status": "Minimal Agri Sarthi backend is running"}

@app.get("/test")
def test_endpoint():
    print("Test endpoint accessed")
    return {"message": "Minimal backend is working!"}

if __name__ == "__main__":
    import uvicorn
    print("Starting minimal server on localhost:8000")
    uvicorn.run(app, host="localhost", port=8000)