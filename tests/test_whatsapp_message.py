"""
Test script to send WhatsApp message via Meta API
Run this script to test if your WhatsApp integration is working
"""
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
RECIPIENT_NUMBER = "923155699929"  # Change this to your test number

def send_template_message(to_number: str):
    """Send a template message (hello_world)"""
    url = f"https://graph.facebook.com/v18.0/837677232754924/messages"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "template",
        "template": {
            "name": "hello_world",
            "language": {
                "code": "en_US"
            }
        }
    }
    
    print(f"Sending template message to {to_number}...")
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    return response

def send_text_message(to_number: str, message: str):
    """Send a simple text message"""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "body": message
        }
    }
    
    print(f"Sending text message to {to_number}...")
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    return response

if __name__ == "__main__":
    print("=" * 50)
    print("WhatsApp Message Test Script")
    print("=" * 50)
    print(f"Phone Number ID: {PHONE_NUMBER_ID}")
    print(f"Access Token: {ACCESS_TOKEN[:20]}..." if ACCESS_TOKEN else "Access Token: Not found")
    print(f"Recipient: {RECIPIENT_NUMBER}")
    print("=" * 50)
    
    # Test 1: Send template message
    print("\n[TEST 1] Sending template message...")
    response1 = send_template_message(RECIPIENT_NUMBER)
    
    if response1.status_code == 200:
        print("✓ Template message sent successfully!")
    else:
        print("✗ Failed to send template message")
        print(f"Error details: {response1.json()}")
    
    print("\n" + "=" * 50)
    
    # Test 2: Send text message (only works within 24-hour window)
    print("\n[TEST 2] Sending text message...")
    print("Note: This will only work if user messaged you in last 24 hours")
    response2 = send_text_message(RECIPIENT_NUMBER, "Hello! This is a test message from Python.")
    
    if response2.status_code == 200:
        print("✓ Text message sent successfully!")
    else:
        print("✗ Failed to send text message")
        try:
            error_data = response2.json()
            print(f"Error details: {error_data}")
        except:
            print(f"Error: {response2.text}")
    
    print("\n" + "=" * 50)
    print("Test completed!")
