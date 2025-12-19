# Payment Tools Refactoring Comparison

## Overview
This document compares the old payment tool implementations (from `tools/booking.py`) with the new refactored versions in `app/agents/tools/payment_tools.py`.

## Key Changes

### Architecture
- **Old**: Direct database access and business logic in tool functions
- **New**: Delegates to `PaymentService` for all business logic

### Dependencies
- **Old**: Direct imports of models, database session, and utility functions
- **New**: Uses service layer (`PaymentService`, `NotificationService`) and repositories

---

## Tool-by-Tool Comparison

### 1. process_payment_screenshot

#### Old Implementation (tools/booking.py)
```python
@tool("process_payment_screenshot" , return_direct=True)
def process_payment_screenshot(booking_id: str = None) -> dict:
    if not booking_id:
        return False

    db = SessionLocal()
    try:
        booking = db.query(Booking).filter_by(booking_id=booking_id).first()
        
        if not booking:
            return {"error": "Booking not found"}

        # Direct database queries and business logic
        booking_date = booking.booking_date.strftime("%d-%m-%Y")
        shift_type = booking.shift_type 
        property_name = booking.property.name 
        # ... more direct access
        
        # Update booking status directly
        booking.status = "Waiting"
        db.commit()
        
        # Complex notification logic inline
        user_session = db.query(Session).filter_by(user_id=booking.user_id).first()
        if not user_session:
            # Fallback logic
        elif user_session.source == "Website":
            save_web_message_to_db(booking.user_id, client_message, sender="bot")
        # ... more inline logic
        
        return message
```

#### New Implementation (app/agents/tools/payment_tools.py)
```python
@tool("process_payment_screenshot", return_direct=True)
def process_payment_screenshot(booking_id: str = None) -> dict:
    if not booking_id:
        return False

    db = SessionLocal()
    try:
        # Use repository for data access
        booking_repo = BookingRepository()
        booking = booking_repo.get_by_booking_id(db, booking_id)
        
        if not booking:
            return {"error": "Booking not found"}

        # Get booking details (same as before)
        booking_date = booking.booking_date.strftime("%d-%m-%Y")
        # ...
        
        # Use repository to update status
        booking_repo.update_status(db, booking_id, "Waiting")
        
        # Delegate notification to service
        notification_service = _get_notification_service()
        session_repo = SessionRepository()
        user_session = session_repo.get_by_user_id(db, booking.user_id)
        
        if user_session and user_session.source == "Website":
            notification_service.save_web_message(booking.user_id, client_message, sender="bot")
        elif user_phone:
            notification_service.send_whatsapp_message_sync(...)
        
        return admin_message
```

**Key Improvements:**
- ✅ Uses `BookingRepository` instead of direct database queries
- ✅ Uses `SessionRepository` for session access
- ✅ Delegates notifications to `NotificationService`
- ✅ Cleaner separation of concerns

---

### 2. process_payment_details

#### Old Implementation (tools/booking.py)
```python
@tool("process_payment_details")
def process_payment_details(
    session_id: str,
    booking_id: str,
    transaction_id: Optional[str] = None,
    sender_name: Optional[str] = None,
    amount: Optional[str] = None,
    sender_phone: Optional[str] = None
) -> dict:
    db = SessionLocal()
    try:
        booking_id = booking_id.strip()
        booking = db.query(Booking).filter_by(booking_id=booking_id).first()
        
        if not booking:
            return {"error": "❌ Booking not found. Please check your booking ID."}
        
        # All validation logic inline
        payment_details = {
            'transaction_id': transaction_id,
            'sender_name': sender_name,
            'amount': amount,
            'sender_phone': sender_phone,
            'receiver_phone': EASYPAISA_NUMBER,
        }
        
        # Clean and validate details (lots of inline logic)
        if payment_details['transaction_id']:
            payment_details['transaction_id'] = re.sub(r'[^A-Z0-9]', '', ...)
        
        # Check required fields
        required_fields = ['sender_name', 'amount']
        missing_fields = []
        # ... validation logic
        
        # Validate amount
        try:
            provided_amount = float(re.sub(r'[^\d.]', '', str(payment_details['amount'])))
            expected_amount = float(booking.total_cost)
            # ... comparison logic
        
        # Get property details with raw SQL
        property_sql = "SELECT name FROM properties WHERE property_id = :property_id"
        property_result = db.execute(text(property_sql), {"property_id": booking.property_id}).first()
        
        # More inline logic for verification
        # ...
```

#### New Implementation (app/agents/tools/payment_tools.py)
```python
@tool("process_payment_details")
def process_payment_details(
    session_id: str,
    booking_id: str,
    transaction_id: Optional[str] = None,
    sender_name: Optional[str] = None,
    amount: Optional[str] = None,
    sender_phone: Optional[str] = None
) -> dict:
    db = SessionLocal()
    try:
        # Delegate all business logic to service
        payment_service = _get_payment_service()
        
        result = payment_service.process_payment_details(
            db=db,
            booking_id=booking_id,
            transaction_id=transaction_id,
            sender_name=sender_name,
            amount=amount,
            sender_phone=sender_phone
        )
        
        # If successful, send admin notification
        if result.get("success"):
            booking_repo = BookingRepository()
            booking = booking_repo.get_by_booking_id(db, booking_id)
            
            if booking:
                # Format admin message (presentation logic only)
                property_name = booking.property.name if booking.property else "Unknown Property"
                payment_details = result.get("payment_details", {})
                admin_message = f"""💳 *Payment Details Received!*
                ...
                """
                print(f"📧 Admin notification: {admin_message}")
        
        return result
```

**Key Improvements:**
- ✅ All validation logic moved to `PaymentService.process_payment_details()`
- ✅ Tool only handles presentation and notification
- ✅ Much cleaner and easier to test
- ✅ Business logic can be reused by other tools/endpoints

---

### 3. confirm_booking_payment

#### Old Implementation (tools/booking.py)
```python
@tool("confirm_booking_payment")
def confirm_booking_payment(booking_id: str) -> dict:
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter_by(booking_id=booking_id).first()
        
        if not booking:
            return {"error": "❌ Booking not found"}
        
        if booking.status == "Confirmed":
            return {
                "success": True,
                "already_confirmed": True,
                "message": "✅ Booking already confirmed",
                "customer_phone": booking.user.phone_number,
                "customer_user_id": booking.user.user_id
            }
        
        # Update booking status directly
        booking.status = "Confirmed"
        booking.updated_at = datetime.now()
        db.commit()
        
        # Get property details with raw SQL
        property_sql = "SELECT name, address, contact_number FROM properties WHERE property_id = :property_id"
        property_result = db.execute(text(property_sql), {"property_id": booking.property_id}).first()
        
        # Format message inline
        confirmation_message = f"""🎉 *BOOKING CONFIRMED!* ✅
        ...
        """

        return {
            "success": True,
            "customer_phone": booking.user.phone_number,
            "customer_user_id": booking.user.user_id,
            "message": confirmation_message
        }
```

#### New Implementation (app/agents/tools/payment_tools.py)
```python
@tool("confirm_booking_payment")
def confirm_booking_payment(booking_id: str) -> dict:
    db = SessionLocal()
    try:
        # Delegate to service
        payment_service = _get_payment_service()
        
        result = payment_service.verify_payment(
            db=db,
            booking_id=booking_id,
            verified_by="admin_agent"
        )
        
        if not result.get("success"):
            return result
        
        # Get booking from result
        booking = result.get("booking")
        if not booking:
            return {"error": "❌ Booking not found after confirmation"}
        
        # Format confirmation message (presentation logic)
        property_name = booking.property.name if booking.property else "Your Selected Property"
        # ...
        
        confirmation_message = f"""🎉 *BOOKING CONFIRMED!* ✅
        ...
        """

        # Send notification using service
        notification_service = _get_notification_service()
        session_repo = SessionRepository()
        user_session = session_repo.get_by_user_id(db, booking.user_id)
        
        if user_session and user_session.source == "Website":
            notification_service.save_web_message(booking.user_id, confirmation_message, sender="bot")
        elif booking.user.phone_number:
            notification_service.send_whatsapp_message_sync(...)
        
        return {
            "success": True,
            "customer_phone": booking.user.phone_number,
            "customer_user_id": booking.user.user_id,
            "message": confirmation_message,
            "already_confirmed": result.get("already_confirmed", False)
        }
```

**Key Improvements:**
- ✅ Uses `PaymentService.verify_payment()` for business logic
- ✅ Uses `NotificationService` for sending messages
- ✅ Tool focuses on presentation and orchestration
- ✅ Easier to test and maintain

---

### 4. reject_booking_payment

#### Old Implementation (tools/booking.py)
```python
@tool("reject_booking_payment")
def reject_booking_payment(booking_id: str, reason: str = None) -> dict:
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter_by(booking_id=booking_id).first()
        
        if not booking:
            return {"error": "❌ Booking not found"}
        
        # Get property name with raw SQL
        property_sql = "SELECT name FROM properties WHERE property_id = :property_id"
        property_result = db.execute(text(property_sql), {"property_id": booking.property_id}).first()
        property_name = property_result[0] if property_result else "Your Property"
        
        # Format rejection message inline
        rejection_message = f"""❌ *PAYMENT VERIFICATION FAILED*
        ...
        """
        
        return {
            "success": True,
            "customer_phone": booking.user.phone_number,
            "customer_user_id": booking.user.user_id,
            "message": rejection_message,
            "booking_status": "Pending",
            "reason": reason
        }
```

#### New Implementation (app/agents/tools/payment_tools.py)
```python
@tool("reject_booking_payment")
def reject_booking_payment(booking_id: str, reason: str = None) -> dict:
    db = SessionLocal()
    try:
        # Validate reason
        if not reason or not reason.strip():
            return {"error": "❌ Rejection reason is required"}
        
        # Delegate to service
        payment_service = _get_payment_service()
        
        result = payment_service.reject_payment(
            db=db,
            booking_id=booking_id,
            reason=reason,
            rejected_by="admin_agent"
        )
        
        if not result.get("success"):
            return result
        
        # Get booking from result
        booking = result.get("booking")
        if not booking:
            return {"error": "❌ Booking not found after rejection"}
        
        # Format rejection message (presentation logic)
        property_name = booking.property.name if booking.property else "Your Property"
        
        rejection_message = f"""❌ *PAYMENT VERIFICATION FAILED*
        ...
        """
        
        # Send notification using service
        notification_service = _get_notification_service()
        session_repo = SessionRepository()
        user_session = session_repo.get_by_user_id(db, booking.user_id)
        
        if user_session and user_session.source == "Website":
            notification_service.save_web_message(booking.user_id, rejection_message, sender="bot")
        elif booking.user.phone_number:
            notification_service.send_whatsapp_message_sync(...)
        
        return {
            "success": True,
            "customer_phone": booking.user.phone_number,
            "customer_user_id": booking.user.user_id,
            "message": rejection_message,
            "booking_status": "Pending",
            "reason": reason
        }
```

**Key Improvements:**
- ✅ Uses `PaymentService.reject_payment()` for business logic
- ✅ Uses `NotificationService` for sending messages
- ✅ Better validation of required fields
- ✅ Cleaner separation of concerns

---

## Summary of Benefits

### 1. Separation of Concerns
- **Old**: Business logic, data access, and presentation mixed together
- **New**: Clear separation - tools handle presentation, services handle business logic, repositories handle data access

### 2. Testability
- **Old**: Hard to test due to direct database access and inline logic
- **New**: Easy to test by mocking services and repositories

### 3. Reusability
- **Old**: Logic locked in tool functions, can't be reused
- **New**: Service methods can be used by tools, API endpoints, and other components

### 4. Maintainability
- **Old**: Changes require modifying tool functions directly
- **New**: Business logic changes happen in services, tools remain stable

### 5. Consistency
- **Old**: Each tool implements its own validation and error handling
- **New**: Consistent validation and error handling through services

---

## Files Modified

1. **app/agents/tools/payment_tools.py** - Refactored all 4 payment tools
2. **test_payment_tools.py** - Created comprehensive tests

## Files Referenced (Not Modified)

1. **tools/booking.py** - Original implementations (will be removed in cleanup phase)
2. **app/services/payment_service.py** - Service layer used by tools
3. **app/services/notification_service.py** - Notification service used by tools
4. **app/repositories/booking_repository.py** - Repository used by tools
5. **app/repositories/session_repository.py** - Repository used by tools

---

## Testing Results

All tests passed successfully:
- ✅ All 4 payment tools imported successfully
- ✅ All tools have correct structure and names
- ✅ Tools handle invalid inputs correctly
- ✅ Tools delegate to PaymentService
- ✅ Notification logic works correctly

---

## Next Steps

1. Update agent imports to use new payment tools (Task 42)
2. Test agent functionality with refactored tools (Task 43)
3. Remove old tool implementations during cleanup (Phase 12)
