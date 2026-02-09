"""Set up WPPConnect session — generates token and starts session."""
import requests
import json

BASE = "http://localhost:21465"
SESSION = "agrisarthi"
SECRET = "THISISMYSECURETOKEN"

# 1. Generate token
print("1. Generating token...")
r = requests.post(f"{BASE}/api/{SESSION}/{SECRET}/generate-token")
print(f"   Status: {r.status_code}")
data = r.json()
print(f"   Response: {json.dumps(data, indent=2)}")

token = data.get("token")
if not token:
    print("   ERROR: No token returned!")
    exit(1)

print(f"\n   TOKEN: {token}")
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

# 2. Start session
print("\n2. Starting session (this will generate QR code)...")
r2 = requests.post(f"{BASE}/api/{SESSION}/start-session", headers=headers)
print(f"   Status: {r2.status_code}")
resp = r2.json()

# Check for QR code
if "qrcode" in str(resp):
    print("   QR Code generated! Check the WPPConnect terminal for the QR code.")
    print("   Or open: http://localhost:21465/api-docs and use start-session endpoint")
else:
    print(f"   Response: {json.dumps(resp, indent=2)[:500]}")

print(f"\n=== Copy this token to .env ===")
print(f"WPPCONNECT_TOKEN={token}")
