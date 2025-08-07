import os
from dotenv import load_dotenv

print("=== ENVIRONMENT DEBUG ===")
print("Before load_dotenv():")
print(f"GROQ_API_KEY: {os.getenv('GROQ_API_KEY')}")
print(f"TAVILY_API_KEY: {os.getenv('TAVILY_API_KEY')}")
print(f"GOOGLE_API_KEY: {os.getenv('GOOGLE_API_KEY')}")

print("\nLoading .env file...")
result = load_dotenv()
print(f"load_dotenv() result: {result}")

print("\nAfter load_dotenv():")
print(f"GROQ_API_KEY: {os.getenv('GROQ_API_KEY')}")
print(f"TAVILY_API_KEY: {os.getenv('TAVILY_API_KEY')}")
print(f"GOOGLE_API_KEY: {os.getenv('GOOGLE_API_KEY')}")

print("\nChecking .env file existence:")
env_path = ".env"
print(f".env file exists: {os.path.exists(env_path)}")
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        content = f.read()
        print(f".env file content length: {len(content)} characters")
        print("First few lines:")
        for i, line in enumerate(content.split('\n')[:5]):
            print(f"  {i+1}: {line}")

print("=== END DEBUG ===")