# Simple test script to verify backend functionality
import sys
import os

print("=== BACKEND TEST SCRIPT ===")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Files in current directory: {os.listdir('.')}")

# Load environment variables FIRST
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ dotenv import and load successful")
    print(f"GROQ_API_KEY loaded: {'Yes' if os.getenv('GROQ_API_KEY') else 'No'}")
    print(f"TAVILY_API_KEY loaded: {'Yes' if os.getenv('TAVILY_API_KEY') else 'No'}")
    print(f"GOOGLE_API_KEY loaded: {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")
except ImportError as e:
    print(f"✗ dotenv import failed: {e}")

try:
    from fastapi import FastAPI
    print("✓ FastAPI import successful")
except ImportError as e:
    print(f"✗ FastAPI import failed: {e}")

try:
    from agent import agentic_workflow
    print("✓ agent import successful")
except ImportError as e:
    print(f"✗ agent import failed: {e}")

print("=== END TEST ===")