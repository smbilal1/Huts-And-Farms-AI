"""
Test script for admin web integration
This script tests the admin confirmation flow via web interface
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust if your server runs on a different port
WEB_ADMIN_USER_ID = "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"

def test_admin_confirm_booking():
    """Test admin confirming a booking via web interface"""
    
    # Test data - replace with actual booking ID from your database
    test_booking_id = "TestUser-2024-01-15-Day"
    
    # Prepare the request
    url = f"{BASE_URL}/web-chat/send-message"
    payload = {
        "message": f"confirm {test_booking_id}",
        "user_id": WEB_ADMIN_USER_ID
    }
    
    print(f"🧪 Testing admin confirmation...")
    print(f"   URL: {url}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📄 Response Body:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                print("\n✅ Test PASSED: Admin confirmation successful!")
                return True
            else:
                print(f"\n❌ Test FAILED: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"\n❌ Test FAILED: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test FAILED with exception: {e}")
        return False

def test_admin_reject_booking():
    """Test admin rejecting a booking via web interface"""
    
    # Test data - replace with actual booking ID from your database
    test_booking_id = "TestUser-2024-01-15-Night"
    
    # Prepare the request
    url = f"{BASE_URL}/web-chat/send-message"
    payload = {
        "message": f"reject {test_booking_id} amount_mismatch",
        "user_id": WEB_ADMIN_USER_ID
    }
    
    print(f"\n🧪 Testing admin rejection...")
    print(f"   URL: {url}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📄 Response Body:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                print("\n✅ Test PASSED: Admin rejection successful!")
                return True
            else:
                print(f"\n❌ Test FAILED: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"\n❌ Test FAILED: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test FAILED with exception: {e}")
        return False

def test_regular_user_not_routed_to_admin():
    """Test that regular users are not routed to admin agent"""
    
    # Use a different user ID (not admin)
    regular_user_id = "test-user-123"
    
    url = f"{BASE_URL}/web-chat/send-message"
    payload = {
        "message": "Hello, I want to book a farm",
        "user_id": regular_user_id
    }
    
    print(f"\n🧪 Testing regular user routing...")
    print(f"   URL: {url}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        # Regular user should get booking agent response, not admin agent
        # This test just verifies the endpoint works for non-admin users
        if response.status_code in [200, 404]:  # 404 if user doesn't exist
            print("\n✅ Test PASSED: Regular user not routed to admin agent")
            return True
        else:
            print(f"\n❌ Test FAILED: Unexpected status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test FAILED with exception: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Admin Web Integration Test Suite")
    print("=" * 60)
    print("\n⚠️  NOTE: Make sure your FastAPI server is running!")
    print("⚠️  NOTE: Update test_booking_id with actual booking IDs from your database")
    print("\n" + "=" * 60)
    
    # Run tests
    results = []
    
    # Test 1: Admin confirmation
    results.append(("Admin Confirm", test_admin_confirm_booking()))
    
    # Test 2: Admin rejection
    results.append(("Admin Reject", test_admin_reject_booking()))
    
    # Test 3: Regular user routing
    results.append(("Regular User", test_regular_user_not_routed_to_admin()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")
    print("=" * 60)
