# Admin Tools - Web & WhatsApp Routing

## Summary

The admin tools (`confirm_booking_payment` and `reject_booking_payment`) now properly work for **both web and WhatsApp customers**. The system automatically detects the customer type and routes the confirmation/rejection message to the correct channel.

## How It Works

### 1. Tools Return Customer Data (No Direct Sending)

Both tools return structured data instead of sending messages directly:

```python
# confirm_booking_payment tool
return {
    "success": True,
    "customer_phone": booking.user.phone_number,  # None for web, phone for WhatsApp
    "customer_user_id": booking.user.user_id,     # UUID
    "message": confirmation_message                # Message to send
}

# reject_booking_payment tool
return {
    "success": True,
    "customer_phone": booking.user.phone_number,
    "customer_user_id": booking.user.user_id,
    "message": rejection_message,
    "booking_status": "Pending",
    "reason": reason
}
```

### 2. Web Routes Handles Routing

The `handle_admin_message` function in `web_routes.py` receives the tool response and routes it:

```python
# Get response from admin agent (which calls the tools)
agent_response = admin_agent.get_response(incoming_text, session_id)

# Extract customer data
customer_phone = agent_response.get("customer_phone")
customer_user_id = agent_response.get("customer_user_id")
customer_message = agent_response.get("message")

# Determine customer type
is_web_customer = not customer_phone or customer_phone == "" or customer_phone == "Web User"

if is_web_customer:
    # Web customer - save to their chat
    save_web_message_to_db(customer_user_id, customer_message, sender="bot")
    admin_feedback = "✅ Confirmation sent to web customer"
else:
    # WhatsApp customer - send via WhatsApp
    send_whatsapp_message_sync(customer_phone, customer_message, customer_user_id, save_to_db=True)
    admin_feedback = f"✅ Confirmation sent to customer via WhatsApp: {customer_phone}"
```

### 3. WhatsApp Webhook Handles Routing

The `wati_webhook.py` does similar routing for WhatsApp admin:

```python
# Admin sends command via WhatsApp
admin_bot_answer = admin_agent.get_response(text, session_id)

# Get customer data
customer_phone = session.user.phone_number
customer_user_id = session.user.user_id

# Send to customer (always WhatsApp in this case)
await send_whatsapp_message(customer_phone, admin_bot_answer)
```

## Customer Type Detection

### Web Customer
- `phone_number` = `None` or `""` (empty string)
- Messages saved to database via `save_web_message_to_db()`
- Customer sees message in web chat interface

### WhatsApp Customer
- `phone_number` = Valid phone number (e.g., "923001234567")
- Messages sent via `send_whatsapp_message_sync()`
- Customer receives WhatsApp message

## Flow Diagrams

### Web Customer Flow
```
Web Customer → Upload Payment Screenshot
                      ↓
              Backend processes
                      ↓
         Admin receives notification (web or WhatsApp)
                      ↓
         Admin sends: "confirm ABC-123"
                      ↓
              Admin Agent processes
                      ↓
         confirm_booking_payment tool
                      ↓
         Returns: {
           customer_phone: None,
           customer_user_id: uuid,
           message: "Confirmation..."
         }
                      ↓
         web_routes detects: is_web_customer = True
                      ↓
         save_web_message_to_db()
                      ↓
         Web Customer sees confirmation in chat ✅
```

### WhatsApp Customer Flow
```
WhatsApp Customer → Upload Payment Screenshot
                           ↓
                   Backend processes
                           ↓
            Admin receives notification (web or WhatsApp)
                           ↓
            Admin sends: "confirm ABC-123"
                           ↓
                   Admin Agent processes
                           ↓
            confirm_booking_payment tool
                           ↓
            Returns: {
              customer_phone: "923001234567",
              customer_user_id: uuid,
              message: "Confirmation..."
            }
                           ↓
            web_routes detects: is_web_customer = False
                           ↓
            send_whatsapp_message_sync()
                           ↓
            WhatsApp Customer receives message ✅
```

## Code Changes Made

### Enhanced Customer Type Detection

**Before** ❌:
```python
if customer_phone and customer_phone != "Web User":
    # WhatsApp
else:
    # Web
```

**After** ✅:
```python
is_web_customer = not customer_phone or customer_phone == "" or customer_phone == "Web User"

if is_web_customer:
    # Web customer
    save_web_message_to_db(...)
else:
    # WhatsApp customer
    send_whatsapp_message_sync(...)
```

### Added Error Handling

```python
# Check WhatsApp send result
result = send_whatsapp_message_sync(...)
if result["success"]:
    admin_feedback = "✅ Confirmation sent"
else:
    admin_feedback = "❌ Failed to send"
```

### Added Logging

```python
print(f"📧 Sent confirmation to web customer: {customer_user_id}")
print(f"📱 Sent confirmation to WhatsApp customer: {customer_phone}")
```

## Testing

### Test Web Customer Confirmation

```bash
# 1. Create booking as web customer
curl -X POST http://localhost:8000/web-chat/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to book White Palace for 2025-10-20 day shift",
    "user_id": "web-customer-001"
  }'

# 2. Upload payment screenshot
curl -X POST http://localhost:8000/web-chat/send-image \
  -H "Content-Type: application/json" \
  -d '{
    "image_data": "base64_or_url",
    "user_id": "web-customer-001",
    "is_base64": false
  }'

# 3. Admin confirms (as web admin)
curl -X POST http://localhost:8000/web-chat/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "confirm John Doe-2025-10-20-Day",
    "user_id": "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"
  }'

# 4. Check customer received confirmation
curl -X POST http://localhost:8000/web-chat/history \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "web-customer-001",
    "limit": 5
  }'

# Expected: Last message should be "🎉 BOOKING CONFIRMED!"
```

### Test WhatsApp Customer Confirmation

```bash
# 1. WhatsApp customer uploads payment (via WhatsApp)
# 2. Admin confirms (via web)
curl -X POST http://localhost:8000/web-chat/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "confirm Ahmed-2025-10-21-Night",
    "user_id": "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"
  }'

# Expected: Customer receives WhatsApp message with confirmation
```

### Test Rejection

```bash
# Admin rejects booking
curl -X POST http://localhost:8000/web-chat/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "reject John Doe-2025-10-20-Day amount_mismatch",
    "user_id": "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"
  }'

# Expected: Customer receives rejection message
```

## Database Verification

### Check Web Customer Messages

```sql
-- Check if web customer received confirmation
SELECT 
    id,
    sender,
    content,
    timestamp
FROM messages 
WHERE user_id = 'web-customer-001'
AND sender = 'bot'
AND content LIKE '%BOOKING CONFIRMED%'
ORDER BY timestamp DESC
LIMIT 1;

-- Should return the confirmation message
```

### Check WhatsApp Customer Messages

```sql
-- Check if WhatsApp customer message was saved
SELECT 
    id,
    sender,
    content,
    whatsapp_message_id,
    timestamp
FROM messages 
WHERE user_id = (SELECT user_id FROM users WHERE phone_number = '923001234567')
AND sender = 'bot'
AND content LIKE '%BOOKING CONFIRMED%'
ORDER BY timestamp DESC
LIMIT 1;

-- Should return the confirmation message with whatsapp_message_id
```

## Admin Feedback Messages

### Success Messages

**Web Customer**:
```
✅ Confirmation sent to web customer (User ID: uuid...)
```

**WhatsApp Customer**:
```
✅ Confirmation sent to customer via WhatsApp: 923001234567
```

### Error Messages

**No Customer ID**:
```
❌ Could not identify customer to send confirmation
```

**WhatsApp Send Failed**:
```
❌ Failed to send WhatsApp message to: 923001234567
```

## Comparison Table

| Aspect | Web Customer | WhatsApp Customer |
|--------|--------------|-------------------|
| Phone Number | None or "" | "923001234567" |
| Detection | `is_web_customer = True` | `is_web_customer = False` |
| Send Method | `save_web_message_to_db()` | `send_whatsapp_message_sync()` |
| Message Storage | Database only | Database + WhatsApp API |
| Customer Sees | Web chat interface | WhatsApp app |
| Admin Feedback | "sent to web customer" | "sent via WhatsApp: phone" |

## Benefits

1. **Unified Admin Experience**: Admin can confirm/reject from web or WhatsApp
2. **Automatic Routing**: System detects customer type automatically
3. **Consistent Behavior**: Same tools work for both platforms
4. **Proper Delivery**: Messages reach customers via their channel
5. **Error Handling**: Admin gets feedback if sending fails
6. **Logging**: All operations logged for debugging

## Future Enhancements

1. **SMS Fallback**: If WhatsApp fails, send SMS
2. **Email Notification**: Send email copy of confirmation
3. **Push Notifications**: For web customers with PWA
4. **Multi-channel**: Send to multiple channels simultaneously
5. **Delivery Status**: Track if customer received/read message

---

**Status**: ✅ Working for both Web and WhatsApp
**Date**: 2025-10-14
**Tested**: Yes
