"""
Script to verify Meta WhatsApp API credentials
This will help diagnose what's wrong with your setup
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

print("=" * 60)
print("META WHATSAPP API CREDENTIALS VERIFICATION")
print("=" * 60)

# Step 1: Check if credentials exist
print("\n[STEP 1] Checking if credentials are set...")
print(f"Phone Number ID: {PHONE_NUMBER_ID}")
print(f"Access Token: {ACCESS_TOKEN[:30]}..." if ACCESS_TOKEN else "Access Token: NOT SET")

if not PHONE_NUMBER_ID or not ACCESS_TOKEN:
    print("\n❌ ERROR: Credentials not found in .env file")
    print("Please set META_PHONE_NUMBER_ID and META_ACCESS_TOKEN in your .env file")
    exit(1)

print("✓ Credentials found")

# Step 2: Verify Phone Number ID exists and is accessible
print("\n[STEP 2] Verifying Phone Number ID...")
url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}"
headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

response = requests.get(url, headers=headers)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    data = response.json()
    print(f"\n✓ Phone Number ID is valid!")
    print(f"  Display Phone: {data.get('display_phone_number', 'N/A')}")
    print(f"  Verified Name: {data.get('verified_name', 'N/A')}")
    print(f"  Quality Rating: {data.get('quality_rating', 'N/A')}")
elif response.status_code == 400:
    print("\n❌ ERROR: Phone Number ID is invalid or inaccessible")
    print("Possible reasons:")
    print("  1. Wrong Phone Number ID")
    print("  2. Access Token doesn't have permission for this phone number")
    print("  3. Phone number belongs to a different WhatsApp Business Account")
elif response.status_code == 190:
    print("\n❌ ERROR: Access Token is invalid or expired")
    print("Please generate a new access token from Meta for Developers")
else:
    print(f"\n❌ ERROR: Unexpected error (Status {response.status_code})")

# Step 3: Check Access Token permissions
print("\n[STEP 3] Checking Access Token info...")
debug_url = f"https://graph.facebook.com/v18.0/debug_token?input_token={ACCESS_TOKEN}"
response = requests.get(debug_url, headers=headers)

if response.status_code == 200:
    data = response.json().get("data", {})
    print(f"✓ Token Info:")
    print(f"  App ID: {data.get('app_id', 'N/A')}")
    print(f"  Valid: {data.get('is_valid', False)}")
    print(f"  Expires: {data.get('expires_at', 'Never')}")
    print(f"  Scopes: {', '.join(data.get('scopes', []))}")
else:
    print(f"⚠ Could not verify token (Status {response.status_code})")

# Step 4: Try to get WhatsApp Business Account info
print("\n[STEP 4] Checking WhatsApp Business Account access...")
# Try to get the WABA ID from phone number
if response.status_code == 200:
    waba_url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}?fields=id,display_phone_number,verified_name"
    response = requests.get(waba_url, headers=headers)
    if response.status_code == 200:
        print("✓ Can access WhatsApp Business Account")
    else:
        print(f"⚠ Limited access to WhatsApp Business Account")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)
print("\nIf you see errors above, follow these steps:")
print("1. Go to https://developers.facebook.com/apps")
print("2. Select your app")
print("3. Go to WhatsApp > API Setup")
print("4. Copy the Phone Number ID (should match above)")
print("5. Click 'Generate access token' and copy the new token")
print("6. Update your .env file with the new values")
print("7. Restart your application")
