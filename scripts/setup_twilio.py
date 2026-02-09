"""Configure Twilio phone number webhook to point to ngrok tunnel."""
import os
import sys
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

SID = os.getenv("TWILIO_ACCOUNT_SID", "")
AUTH = os.getenv("TWILIO_AUTH_TOKEN", "")
PHONE = os.getenv("TWILIO_PHONE_NUMBER", "")
NGROK = sys.argv[1] if len(sys.argv) > 1 else input("Enter ngrok URL: ").strip()

if not all([SID, AUTH, PHONE]):
    print("ERROR: Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER in .env")
    sys.exit(1)

# Get current phone number config
url = f"https://api.twilio.com/2010-04-01/Accounts/{SID}/IncomingPhoneNumbers.json"
r = requests.get(url, params={"PhoneNumber": PHONE}, auth=HTTPBasicAuth(SID, AUTH))
numbers = r.json().get("incoming_phone_numbers", [])
if numbers:
    num_sid = numbers[0]["sid"]
    current_url = numbers[0].get("voice_url", "none")
    print(f"Phone SID: {num_sid}")
    print(f"Current voice URL: {current_url}")

    # Update webhook URL
    update_url = f"https://api.twilio.com/2010-04-01/Accounts/{SID}/IncomingPhoneNumbers/{num_sid}.json"
    resp = requests.post(
        update_url,
        data={
            "VoiceUrl": f"{NGROK}/voice/incoming-call",
            "VoiceMethod": "POST",
        },
        auth=HTTPBasicAuth(SID, AUTH),
    )
    if resp.status_code == 200:
        print(f"Updated voice URL to: {NGROK}/voice/incoming-call")
    else:
        print(f"Error updating: {resp.status_code} {resp.text[:300]}")
else:
    print("Phone number not found")
