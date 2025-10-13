# Admin Agent Testing Guide

## Prerequisites

1. **Admin User ID**: `216d5ab6-e8ef-4a5c-8b7c-45be19b28334`
2. **Admin WhatsApp**: `923155699929`
3. **Test Customer User**: Any valid user_id from your database
4. **API Base URL**: Your server URL (e.g., `http://localhost:8000`)

## Test Scenarios

### Scenario 1: Web Customer → Web Admin → Web Customer

#### Step 1: Create Booking as Web Customer
```bash
POST /web-chat/send-message
{
  "message": "I want to book White Palace for 2025-10-20 day shift",
  "user_id": "test-customer-web-001"
}
```

#### Step 2: Provide Booking Details
```bash
POST /web-chat/send-message
{
  "message": "My name is John Doe and CNIC is 1234567890123",
  "user_id": "test-customer-web-001"
}
```

#### Step 3: Upload Payment Screenshot
```bash
POST /web-chat/send-image
{
  "image_url": "https://res.cloudinary.com/your-cloud/image/upload/payment.jpg",
  "user_id": "test-customer-web-001"
}
```

**Expected**: 
- Customer receives: "Payment screenshot received and sent to admin for verification"
- Admin receives verification request in their chat

#### Step 4: Check Admin Notifications
```bash
GET /web-chat/admin/notifications
```

**Expected**: Returns list of pending verifications including the one from Step 3

#### Step 5: Get Admin Chat History
```bash
POST /web-chat/history
{
  "user_id": "216d5ab6-e8ef-4a5c-8b7c-45be19b28334",
  "limit": 10
}
```

**Expected**: Shows verification request message

#### Step 6: Admin Confirms Booking
```bash
POST /web-chat/send-message
{
  "message": "confirm John Doe-2025-10-20-Day",
  "user_id": "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"
}
```

**Expected**:
- Admin receives: "✅ Confirmation sent to web customer"
- Customer receives confirmation in their chat

#### Step 7: Verify Customer Received Confirmation
```bash
POST /web-chat/history
{
  "user_id": "test-customer-web-001",
  "limit": 10
}
```

**Expected**: Last message is "🎉 BOOKING CONFIRMED!"

---

### Scenario 2: Web Customer → Web Admin → Rejection

#### Step 1-3: Same as Scenario 1

#### Step 4: Admin Rejects Booking
```bash
POST /web-chat/send-message
{
  "message": "reject John Doe-2025-10-20-Day amount_mismatch",
  "user_id": "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"
}
```

**Expected**:
- Admin receives: "✅ Rejection sent to web customer"
- Customer receives rejection with reason

#### Step 5: Verify Customer Received Rejection
```bash
POST /web-chat/history
{
  "user_id": "test-customer-web-001",
  "limit": 10
}
```

**Expected**: Last message is "❌ PAYMENT VERIFICATION FAILED"

---

### Scenario 3: WhatsApp Customer → Web Admin → WhatsApp Customer

#### Step 1: WhatsApp Customer Uploads Payment
(This happens via WhatsApp webhook, simulated here)

**Expected**: 
- Verification request saved to web admin's chat
- Can be retrieved via `/web-chat/admin/notifications`

#### Step 2: Web Admin Confirms
```bash
POST /web-chat/send-message
{
  "message": "confirm Ahmed-2025-10-21-Night",
  "user_id": "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"
}
```

**Expected**:
- Admin receives: "✅ Confirmation sent to customer via WhatsApp: 923001234567"
- Customer receives WhatsApp message with confirmation

---

### Scenario 4: Invalid Commands

#### Test 1: Invalid Booking ID
```bash
POST /web-chat/send-message
{
  "message": "confirm INVALID-BOOKING-ID",
  "user_id": "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"
}
```

**Expected**: Admin receives error message "❌ Booking not found"

#### Test 2: Malformed Command
```bash
POST /web-chat/send-message
{
  "message": "confirmm John Doe-2025-10-20-Day",
  "user_id": "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"
}
```

**Expected**: Admin agent responds with help message or error

#### Test 3: Missing Reason for Rejection
```bash
POST /web-chat/send-message
{
  "message": "reject John Doe-2025-10-20-Day",
  "user_id": "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"
}
```

**Expected**: Rejection sent with reason "None" or default reason

---

## Manual Testing Checklist

### ✅ Web Admin Functionality
- [ ] Admin can receive verification requests
- [ ] Admin can view notifications via API
- [ ] Admin can confirm bookings
- [ ] Admin can reject bookings with reason
- [ ] Admin receives feedback after each action
- [ ] Admin messages are saved with sender="admin"
- [ ] Admin bot responses are saved with sender="bot"

### ✅ Customer Notification Routing
- [ ] Web customers receive messages in their chat
- [ ] WhatsApp customers receive WhatsApp messages
- [ ] Messages are saved to database correctly
- [ ] No duplicate messages sent
- [ ] Message content is formatted correctly

### ✅ Error Handling
- [ ] Invalid booking IDs return error
- [ ] Missing customer data handled gracefully
- [ ] Network errors don't crash the system
- [ ] Database errors are logged
- [ ] Admin receives error feedback

### ✅ Cross-Platform Testing
- [ ] Web customer → Web admin → Web customer
- [ ] Web customer → WhatsApp admin → Web customer
- [ ] WhatsApp customer → Web admin → WhatsApp customer
- [ ] WhatsApp customer → WhatsApp admin → WhatsApp customer

### ✅ Database Integrity
- [ ] Messages have correct user_id
- [ ] Messages have correct sender field
- [ ] Timestamps are accurate
- [ ] No orphaned messages
- [ ] Booking status updates correctly

---

## Automated Test Script (Python)

```python
import requests
import time

BASE_URL = "http://localhost:8000"
ADMIN_USER_ID = "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"
TEST_CUSTOMER_ID = "test-customer-001"

def test_full_flow():
    print("🧪 Starting Admin Agent Test Flow\n")
    
    # Step 1: Customer creates booking
    print("1️⃣ Customer creates booking...")
    response = requests.post(f"{BASE_URL}/web-chat/send-message", json={
        "message": "I want to book White Palace for 2025-10-20 day shift",
        "user_id": TEST_CUSTOMER_ID
    })
    print(f"   Response: {response.json()['bot_response'][:50]}...\n")
    time.sleep(1)
    
    # Step 2: Customer provides details
    print("2️⃣ Customer provides details...")
    response = requests.post(f"{BASE_URL}/web-chat/send-message", json={
        "message": "My name is Test User and CNIC is 1234567890123",
        "user_id": TEST_CUSTOMER_ID
    })
    print(f"   Response: {response.json()['bot_response'][:50]}...\n")
    time.sleep(1)
    
    # Step 3: Customer uploads payment (simulated)
    print("3️⃣ Customer uploads payment screenshot...")
    response = requests.post(f"{BASE_URL}/web-chat/send-image", json={
        "image_url": "https://example.com/payment.jpg",
        "user_id": TEST_CUSTOMER_ID
    })
    print(f"   Response: {response.json()['bot_response'][:50]}...\n")
    time.sleep(1)
    
    # Step 4: Check admin notifications
    print("4️⃣ Checking admin notifications...")
    response = requests.get(f"{BASE_URL}/web-chat/admin/notifications")
    notifications = response.json()
    print(f"   Found {notifications['count']} notifications\n")
    time.sleep(1)
    
    # Step 5: Admin confirms booking
    print("5️⃣ Admin confirms booking...")
    response = requests.post(f"{BASE_URL}/web-chat/send-message", json={
        "message": "confirm Test User-2025-10-20-Day",
        "user_id": ADMIN_USER_ID
    })
    print(f"   Admin feedback: {response.json()['bot_response']}\n")
    time.sleep(1)
    
    # Step 6: Verify customer received confirmation
    print("6️⃣ Verifying customer received confirmation...")
    response = requests.post(f"{BASE_URL}/web-chat/history", json={
        "user_id": TEST_CUSTOMER_ID,
        "limit": 5
    })
    messages = response.json()
    last_message = messages[-1]['content']
    
    if "BOOKING CONFIRMED" in last_message:
        print("   ✅ SUCCESS: Customer received confirmation!\n")
    else:
        print("   ❌ FAILED: Customer did not receive confirmation\n")
    
    print("🎉 Test completed!")

if __name__ == "__main__":
    test_full_flow()
```

---

## Common Issues and Solutions

### Issue 1: Admin not detected
**Symptom**: Admin commands processed as regular user messages
**Solution**: Verify `WEB_ADMIN_USER_ID` matches exactly in both files:
- `app/routers/web_routes.py`
- `tools/booking.py`

### Issue 2: Customer not receiving messages
**Symptom**: Admin gets confirmation but customer doesn't receive message
**Solution**: 
- Check if `customer_user_id` is correct in tool response
- Verify `save_web_message_to_db()` is being called
- Check database for message record

### Issue 3: WhatsApp messages not sending
**Symptom**: Web customers work but WhatsApp customers don't receive messages
**Solution**:
- Verify `WHATSAPP_TOKEN` and `PHONE_NUMBER_ID` are set
- Check `send_whatsapp_message_sync()` function
- Verify customer has valid phone number

### Issue 4: Duplicate messages
**Symptom**: Customer receives multiple confirmation messages
**Solution**:
- Check if tool is sending message AND webhook is sending
- Ensure tools only return data, don't send directly
- Verify no duplicate calls to send functions

---

## Performance Testing

### Load Test: Multiple Concurrent Verifications
```python
import concurrent.futures
import requests

def send_admin_command(booking_id):
    response = requests.post(f"{BASE_URL}/web-chat/send-message", json={
        "message": f"confirm {booking_id}",
        "user_id": ADMIN_USER_ID
    })
    return response.status_code == 200

# Test 10 concurrent confirmations
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    booking_ids = [f"Test-{i}-2025-10-20-Day" for i in range(10)]
    results = list(executor.map(send_admin_command, booking_ids))
    
print(f"Success rate: {sum(results)}/{len(results)}")
```

---

## Monitoring and Logging

### Key Logs to Monitor:
1. `📥 Admin input:` - Admin command received
2. `🤖 Agent response:` - Admin agent processing
3. `✅ Confirmation sent to customer` - Success message
4. `❌ Error in handle_admin_message:` - Error occurred

### Database Queries for Monitoring:
```sql
-- Count pending verifications
SELECT COUNT(*) FROM messages 
WHERE user_id = '216d5ab6-e8ef-4a5c-8b7c-45be19b28334'
AND sender = 'bot'
AND content LIKE '%PAYMENT VERIFICATION REQUEST%';

-- Recent admin actions
SELECT * FROM messages 
WHERE user_id = '216d5ab6-e8ef-4a5c-8b7c-45be19b28334'
AND sender = 'admin'
ORDER BY timestamp DESC
LIMIT 10;

-- Confirmed bookings today
SELECT * FROM bookings 
WHERE status = 'Confirmed'
AND DATE(updated_at) = CURRENT_DATE;
```
