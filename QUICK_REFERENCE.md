# Admin Agent Quick Reference Card

## 🔑 Configuration

```python
WEB_ADMIN_USER_ID = "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"
VERIFICATION_WHATSAPP = "923155699929"
```

## 📡 API Endpoints

### Admin Endpoints
```bash
# Send admin command
POST /web-chat/send-message
{
  "message": "confirm ABC-123",
  "user_id": "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"
}

# Get pending verifications
GET /web-chat/admin/notifications

# Get admin chat history
POST /web-chat/history
{
  "user_id": "216d5ab6-e8ef-4a5c-8b7c-45be19b28334",
  "limit": 20
}
```

### Customer Endpoints
```bash
# Send message
POST /web-chat/send-message
{
  "message": "I want to book...",
  "user_id": "customer-001"
}

# Upload payment
POST /web-chat/send-image
{
  "image_url": "https://...",
  "user_id": "customer-001"
}

# Get history
POST /web-chat/history
{
  "user_id": "customer-001",
  "limit": 50
}
```

## 💬 Admin Commands

### Confirm Booking
```
confirm <booking_id>
```
Example: `confirm John Doe-2025-10-20-Day`

### Reject Booking
```
reject <booking_id> <reason>
```
Examples:
- `reject John Doe-2025-10-20-Day amount_mismatch`
- `reject John Doe-2025-10-20-Day transaction_not_found`
- `reject John Doe-2025-10-20-Day insufficient_amount`

### Common Rejection Reasons
- `amount_mismatch` - Wrong amount paid
- `transaction_not_found` - Can't verify transaction
- `insufficient_amount` - Amount less than required
- `incorrect_receiver` - Wrong EasyPaisa number
- `duplicate_transaction` - Transaction already used
- `invalid_details` - Details don't match

## 🔄 Message Flow

```
Customer → Upload Payment
         ↓
Admin ← Verification Request
         ↓
Admin → Confirm/Reject Command
         ↓
System → Routes to Customer
         ↓
Customer ← Confirmation/Rejection
```

## 🎯 Key Functions

### In web_routes.py
```python
# Admin detection
if user_id == WEB_ADMIN_USER_ID:
    # Process as admin

# Customer routing
if customer_phone and customer_phone != "Web User":
    send_whatsapp_message_sync(...)  # WhatsApp
else:
    save_web_message_to_db(...)      # Web
```

### In booking.py
```python
# Tool return structure
return {
    "success": True,
    "customer_phone": "923001234567",
    "customer_user_id": "uuid...",
    "message": "Confirmation message"
}
```

## 📊 Database Queries

### Check Pending Verifications
```sql
SELECT COUNT(*) FROM messages 
WHERE user_id = '216d5ab6-e8ef-4a5c-8b7c-45be19b28334'
AND sender = 'bot'
AND content LIKE '%PAYMENT VERIFICATION REQUEST%';
```

### Recent Admin Actions
```sql
SELECT * FROM messages 
WHERE user_id = '216d5ab6-e8ef-4a5c-8b7c-45be19b28334'
AND sender = 'admin'
ORDER BY timestamp DESC
LIMIT 10;
```

### Today's Confirmations
```sql
SELECT * FROM bookings 
WHERE status = 'Confirmed'
AND DATE(updated_at) = CURRENT_DATE;
```

## 🐛 Debugging

### Check Logs
```bash
# Admin command received
📥 Admin input: confirm ABC-123

# Agent processing
🤖 Agent response: {...}

# Success
✅ Confirmation sent to customer via WhatsApp

# Error
❌ Error in admin flow: ...
```

### Common Issues

**Issue**: Admin not detected
```python
# Check: user_id matches exactly
print(f"User ID: {user_id}")
print(f"Admin ID: {WEB_ADMIN_USER_ID}")
print(f"Match: {user_id == WEB_ADMIN_USER_ID}")
```

**Issue**: Customer not receiving message
```python
# Check: customer data in tool response
print(f"Tool response: {admin_bot_answer}")
print(f"Has customer_phone: {'customer_phone' in admin_bot_answer}")
print(f"Customer phone: {admin_bot_answer.get('customer_phone')}")
```

**Issue**: Wrong channel used
```python
# Check: phone number detection
print(f"Customer phone: {customer_phone}")
print(f"Is web: {customer_phone is None or customer_phone == 'Web User'}")
```

## 🧪 Quick Test

```bash
# 1. Upload payment
curl -X POST http://localhost:8000/web-chat/send-image \
  -H "Content-Type: application/json" \
  -d '{"image_url":"https://...", "user_id":"test-001"}'

# 2. Check notifications
curl http://localhost:8000/web-chat/admin/notifications

# 3. Confirm booking
curl -X POST http://localhost:8000/web-chat/send-message \
  -H "Content-Type: application/json" \
  -d '{"message":"confirm Test-2025-10-20-Day", "user_id":"216d5ab6-e8ef-4a5c-8b7c-45be19b28334"}'

# 4. Verify customer received
curl -X POST http://localhost:8000/web-chat/history \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test-001", "limit":5}'
```

## 📝 Response Examples

### Admin Confirmation Success
```json
{
  "status": "success",
  "bot_response": "✅ Confirmation sent to customer via WhatsApp: 923001234567",
  "message_id": 123
}
```

### Admin Rejection Success
```json
{
  "status": "success",
  "bot_response": "✅ Rejection sent to web customer",
  "message_id": 124
}
```

### Error Response
```json
{
  "status": "error",
  "error": "❌ Booking not found"
}
```

### Notifications Response
```json
{
  "status": "success",
  "notifications": [
    {
      "message_id": 100,
      "content": "🔔 PAYMENT VERIFICATION REQUEST...",
      "timestamp": "2025-10-13T10:30:00",
      "is_read": false
    }
  ],
  "count": 1
}
```

## 🔐 Security Checklist

- [ ] Admin user ID is kept secret
- [ ] Only authorized users have admin ID
- [ ] Admin messages logged with sender="admin"
- [ ] Customer data not exposed in admin responses
- [ ] Booking IDs validated before processing
- [ ] Error messages don't leak sensitive info

## 📚 Documentation Files

1. **IMPLEMENTATION_SUMMARY.md** - Quick overview
2. **ADMIN_WEB_IMPLEMENTATION.md** - Detailed guide
3. **ADMIN_FLOW_DIAGRAM.md** - Visual diagrams
4. **TESTING_GUIDE.md** - Testing instructions
5. **BEFORE_AFTER_COMPARISON.md** - What changed
6. **QUICK_REFERENCE.md** - This file

## 🆘 Support

**Need help?**
1. Check logs for error messages
2. Verify configuration constants
3. Review TESTING_GUIDE.md
4. Check database records
5. Test with simple flow first

**Common Commands:**
```bash
# Check if admin user exists
SELECT * FROM users WHERE user_id = '216d5ab6-e8ef-4a5c-8b7c-45be19b28334';

# Check admin session
SELECT * FROM sessions WHERE user_id = '216d5ab6-e8ef-4a5c-8b7c-45be19b28334';

# Check recent admin messages
SELECT * FROM messages 
WHERE user_id = '216d5ab6-e8ef-4a5c-8b7c-45be19b28334'
ORDER BY timestamp DESC LIMIT 5;
```

---

**Version**: 1.0  
**Last Updated**: 2025-10-13  
**Status**: ✅ Production Ready
