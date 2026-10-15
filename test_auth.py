import requests
import json
import uuid
import time
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1/auth"

print("="*50)
print("Testing Auth API")
print("="*50)

# Wait a second for the server to start
time.sleep(2)

unique_id = uuid.uuid4().hex[:6]
test_email = f"test_{unique_id}@example.com"
test_username = f"user_{unique_id}"

# 1. Register
print(f"\n[1] Registering new user ({test_email})...")
register_data = {
    "name": "Test User",
    "username": test_username,
    "email": test_email
}
try:
    response = requests.post(f"{BASE_URL}/register", json=register_data)
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print(response.text)
except requests.exceptions.ConnectionError:
    print("ConnectionError: Failed to connect to the API. Make sure the server is running.")
    sys.exit(1)

# 2. Request OTP
print(f"\n[2] Requesting OTP for {test_email}...")
otp_data = {
    "identifier": test_email
}
response = requests.post(f"{BASE_URL}/request-otp", json=otp_data)
print(f"Status Code: {response.status_code}")
try:
    print(json.dumps(response.json(), indent=2))
except Exception:
    print(response.text)

print("\n(Note: Verifying OTP requires the code sent to the email, so it's skipped here.)")
print("="*50)
