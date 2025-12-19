# NotificationService Integration Guide

## Overview
This guide shows how to integrate the `NotificationService` into existing services and endpoints.

## Quick Start

### 1. Import the Service
```python
from app.services.notification_service import NotificationService
from app.integrations.whatsapp import WhatsAppClient
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
```

### 2. Initialize Dependencies
```python
# Create dependencies
whatsapp_client = WhatsAppClient()
message_repo = MessageRepository()
session_repo = SessionRepository()

# Create notification service
notification_service = NotificationService(
    whatsapp_client=whatsapp_client,
    message_repo=message_repo,
    session_repo=session_repo
)
```

### 3. Use in Your Service
```python
# Send notification
result = await notification_service.notify_booking_confirmed(
    db=db_session,
    booking=booking,
    confirmed_by="admin"
)

if result["success"]:
    print(f"Notification sent via {result['channel']}")
else:
    print(f"Failed: {result['error']}")
```

## Integration Examples

### Example 1: Payment Service Integration

```python
# app/services/payment_service.py

class PaymentService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        gemini_client: GeminiClient,
        cloudinary_client: CloudinaryClient,
        notification_service: NotificationService  # Add this
    ):
        self.booking_repo = booking_repo
        self.gemini_client = gemini_client
        self.cloudinary_client = cloudinary_client
        self.notification_service = notification_service  # Add this
    
    async def process_payment_screenshot(
        self,
        db: Session,
        booking_id: str,
        image_data: str,
        is_base64: bool = True
    ) -> Dict:
        # ... existing code to process screenshot ...
        
        # Update booking status
        self.booking_repo.update_status(db, booking_id, "Waiting")
        
        # Notify customer
        await self.notification_service.notify_customer_payment_received(
            db=db,
            booking=booking
        )
        
        # Notify admin
        await self.notification_service.notify_admin_payment_received(
            db=db,
            booking=booking,
            payment_details=payment_info,
            image_url=image_url
        )
        
        return {"success": True, "message": "Payment received"}
```

### Example 2: Booking Service Integration

```python
# app/services/booking_service.py

class BookingService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        property_repo: PropertyRepository,
        user_repo: UserRepository,
        notification_service: NotificationService  # Add this
    ):
        self.booking_repo = booking_repo
        self.property_repo = property_repo
        self.user_repo = user_repo
        self.notification_service = notification_service  # Add this
    
    async def confirm_booking(
        self,
        db: Session,
        booking_id: str,
        confirmed_by: str = "admin"
    ) -> Dict:
        # Get booking
        booking = self.booking_repo.get_by_booking_id(db, booking_id)
        
        if not booking:
            return {"error": "Booking not found"}
        
        if booking.status == "Confirmed":
            return {"error": "Booking already confirmed"}
        
        # Update status
        booking = self.booking_repo.update_status(db, booking_id, "Confirmed")
        
        # Send notification
        result = await self.notification_service.notify_booking_confirmed(
            db=db,
            booking=booking,
            confirmed_by=confirmed_by
        )
        
        return {
            "success": True,
            "booking": booking,
            "notification_sent": result["success"],
            "message": result.get("message", "")
        }
    
    async def cancel_booking(
        self,
        db: Session,
        booking_id: str,
        reason: Optional[str] = None,
        cancelled_by: str = "user"
    ) -> Dict:
        # Get booking
        booking = self.booking_repo.get_by_booking_id(db, booking_id)
        
        if not booking:
            return {"error": "Booking not found"}
        
        # Update status
        booking = self.booking_repo.update_status(db, booking_id, "Cancelled")
        
        # Send notification
        result = await self.notification_service.notify_booking_cancelled(
            db=db,
            booking=booking,
            reason=reason,
            cancelled_by=cancelled_by
        )
        
        return {
            "success": True,
            "booking": booking,
            "notification_sent": result["success"],
            "message": result.get("message", "")
        }
```

### Example 3: API Endpoint Integration

```python
# app/api/v1/admin.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.dependencies import get_booking_service, get_db

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/bookings/{booking_id}/confirm")
async def confirm_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    booking_service: BookingService = Depends(get_booking_service)
):
    """Confirm a booking after payment verification."""
    result = await booking_service.confirm_booking(
        db=db,
        booking_id=booking_id,
        confirmed_by="admin"
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "success": True,
        "booking_id": booking_id,
        "status": "Confirmed",
        "notification_sent": result["notification_sent"]
    }

@router.post("/bookings/{booking_id}/reject")
async def reject_booking(
    booking_id: str,
    reason: str,
    db: Session = Depends(get_db),
    booking_service: BookingService = Depends(get_booking_service)
):
    """Reject a booking and notify customer."""
    result = await booking_service.cancel_booking(
        db=db,
        booking_id=booking_id,
        reason=reason,
        cancelled_by="admin"
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "success": True,
        "booking_id": booking_id,
        "status": "Cancelled",
        "notification_sent": result["notification_sent"]
    }
```

### Example 4: Dependency Injection Setup

```python
# app/api/dependencies.py

from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.notification_service import NotificationService
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService
from app.integrations.whatsapp import WhatsAppClient
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.booking_repository import BookingRepository

# Integration clients
def get_whatsapp_client() -> WhatsAppClient:
    return WhatsAppClient()

# Repositories
def get_message_repo() -> MessageRepository:
    return MessageRepository()

def get_session_repo() -> SessionRepository:
    return SessionRepository()

def get_booking_repo() -> BookingRepository:
    return BookingRepository()

# Notification service
def get_notification_service(
    whatsapp_client: WhatsAppClient = Depends(get_whatsapp_client),
    message_repo: MessageRepository = Depends(get_message_repo),
    session_repo: SessionRepository = Depends(get_session_repo)
) -> NotificationService:
    return NotificationService(
        whatsapp_client=whatsapp_client,
        message_repo=message_repo,
        session_repo=session_repo
    )

# Booking service with notification
def get_booking_service(
    booking_repo: BookingRepository = Depends(get_booking_repo),
    notification_service: NotificationService = Depends(get_notification_service)
) -> BookingService:
    return BookingService(
        booking_repo=booking_repo,
        # ... other dependencies ...
        notification_service=notification_service
    )
```

## Message Customization

### Customizing Notification Messages

If you need to customize messages, you can extend the service:

```python
class CustomNotificationService(NotificationService):
    """Extended notification service with custom messages."""
    
    async def notify_booking_confirmed(
        self,
        db: Session,
        booking: Any,
        confirmed_by: str = "admin"
    ) -> Dict[str, Any]:
        # Add custom logic before sending
        if booking.property.type == "Premium":
            # Send premium confirmation with extra details
            pass
        
        # Call parent method
        return await super().notify_booking_confirmed(
            db, booking, confirmed_by
        )
```

## Error Handling

### Handling Notification Failures

```python
async def process_with_notification(db: Session, booking_id: str):
    """Process booking and handle notification failures gracefully."""
    try:
        # Update booking
        booking = booking_repo.update_status(db, booking_id, "Confirmed")
        
        # Try to send notification
        result = await notification_service.notify_booking_confirmed(
            db=db,
            booking=booking
        )
        
        if not result["success"]:
            # Log error but don't fail the operation
            logger.error(f"Notification failed: {result['error']}")
            # Could retry later or alert admin
        
        return {"success": True, "booking": booking}
        
    except Exception as e:
        # Handle booking update errors
        logger.error(f"Booking update failed: {e}")
        return {"success": False, "error": str(e)}
```

## Testing Integration

### Unit Test with Mocked Notification Service

```python
@pytest.mark.asyncio
async def test_booking_confirmation_with_notification():
    """Test booking confirmation sends notification."""
    # Mock dependencies
    booking_repo = Mock()
    notification_service = Mock()
    
    # Setup mocks
    booking = Mock()
    booking.status = "Waiting"
    booking_repo.get_by_booking_id.return_value = booking
    booking_repo.update_status.return_value = booking
    
    notification_service.notify_booking_confirmed = AsyncMock(
        return_value={"success": True, "message": "Sent"}
    )
    
    # Create service
    service = BookingService(
        booking_repo=booking_repo,
        notification_service=notification_service
    )
    
    # Test
    result = await service.confirm_booking(Mock(), "test-booking-id")
    
    # Verify
    assert result["success"] is True
    notification_service.notify_booking_confirmed.assert_called_once()
```

## Best Practices

### 1. Always Use Async/Await
```python
# ✅ Correct
result = await notification_service.notify_booking_confirmed(db, booking)

# ❌ Wrong
result = notification_service.notify_booking_confirmed(db, booking)
```

### 2. Handle Notification Failures Gracefully
```python
# ✅ Correct - Don't fail the main operation
result = await notification_service.notify_booking_confirmed(db, booking)
if not result["success"]:
    logger.warning(f"Notification failed: {result['error']}")
    # Continue with main operation

# ❌ Wrong - Don't raise exceptions for notification failures
if not result["success"]:
    raise Exception("Notification failed")
```

### 3. Check Success Status
```python
# ✅ Correct
result = await notification_service.notify_booking_confirmed(db, booking)
if result["success"]:
    print(f"Sent via {result['channel']}")
else:
    print(f"Failed: {result['error']}")

# ❌ Wrong - Don't assume success
result = await notification_service.notify_booking_confirmed(db, booking)
print(result["message"])  # Might not exist if failed
```

### 4. Use Dependency Injection
```python
# ✅ Correct - Inject dependencies
def __init__(self, notification_service: NotificationService):
    self.notification_service = notification_service

# ❌ Wrong - Don't create instances directly
def __init__(self):
    self.notification_service = NotificationService(...)
```

## Troubleshooting

### Issue: Notifications Not Sending

**Check:**
1. Environment variables configured (META_ACCESS_TOKEN, etc.)
2. WhatsApp client initialized correctly
3. User has phone number (for WhatsApp)
4. Session source is set correctly

**Debug:**
```python
result = await notification_service.notify_booking_confirmed(db, booking)
print(f"Success: {result['success']}")
print(f"Channel: {result.get('channel')}")
print(f"Error: {result.get('error')}")
```

### Issue: Wrong Channel Used

**Check:**
1. Session source ("Website" vs "Chatbot")
2. User phone number availability
3. Fallback logic working correctly

**Debug:**
```python
session = session_repo.get_by_user_id(db, booking.user_id)
print(f"Session source: {session.source if session else 'None'}")
print(f"User phone: {booking.user.phone_number}")
```

## Migration from Old Code

### Before (Old Pattern)
```python
# Old code in tools/booking.py
def send_whatsapp_message_sync(recipient, message, user_id):
    # Direct WhatsApp API call
    response = requests.post(url, json=payload, headers=headers)
    # Save to database
    save_bot_message_to_db(user_id, message, msg_id)
```

### After (New Pattern)
```python
# New code using NotificationService
result = await notification_service.notify_booking_confirmed(
    db=db,
    booking=booking
)
# Handles routing, sending, and saving automatically
```

## Summary

The NotificationService provides:
- ✅ Unified interface for all notifications
- ✅ Automatic channel routing (WhatsApp/Web)
- ✅ Professional message formatting
- ✅ Error handling and fallbacks
- ✅ Easy testing with dependency injection
- ✅ Consistent behavior across the application

For more examples, see:
- `test_notification_service.py` - Comprehensive test suite
- `demo_notification_service.py` - Usage demonstrations
- `TASK_22_SUMMARY.md` - Implementation details
