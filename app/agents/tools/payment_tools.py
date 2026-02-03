"""
Payment-related agent tools.

This module contains tools for:
- Processing payment screenshots
- Processing payment details
- Confirming booking payments
- Rejecting booking payments

All tools delegate business logic to PaymentService.
"""

from langchain.tools import tool
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.payment_service import PaymentService
from app.services.notification_service import NotificationService
from app.repositories.booking_repository import BookingRepository
from app.repositories.session_repository import SessionRepository


def _get_payment_service() -> PaymentService:
    """Get PaymentService instance with dependencies."""
    return PaymentService()


def _get_notification_service() -> NotificationService:
    """Get NotificationService instance with dependencies."""
    return NotificationService()


@tool("process_payment_screenshot", return_direct=True)
def process_payment_screenshot(booking_id: str = None) -> dict:
    """
    Process payment screenshot for a booking.
    If no booking ID is provided, return False.
    Else, return Payment details.
    
    This tool:
    1. Updates booking status to "Waiting"
    2. Sends notification to admin for verification
    3. Sends confirmation to customer
    
    Args:
        booking_id: The booking ID to process payment for
        
    Returns:
        Payment processing status and verification message
    """
    if not booking_id:
        return False

    db = SessionLocal()
    try:
        # Get services
        booking_repo = BookingRepository()
        
        # Get booking
        booking = booking_repo.get_by_booking_id(db, booking_id)
        
        if not booking:
            return {"error": "Booking not found"}

        # Get booking details
        booking_date = booking.booking_date.strftime("%d-%m-%Y")
        shift_type = booking.shift_type 
        property_name = booking.property.name 
        property_type = booking.property.type
        total_cost = booking.total_cost
        user_phone = booking.user.phone_number
        user_cnic = booking.user.cnic
        
        # Update booking status to Waiting
        booking_repo.update_status(db, booking_id, "Waiting")
        
        # Mark state change for memory system
        from app.agents.memory.state_detector import mark_state_change
        session_repo = SessionRepository()
        user_session = session_repo.get_by_user_id(db, booking.user_id)
        if user_session:
            mark_state_change(user_session.id, db)
        
        # Format admin notification message
        admin_message = f"""📸 *Payment Screenshot Received!*

Booking ID: `{booking_id}`
Property: *{property_name}*
Type: {property_type}
Date: {booking_date}
Shift: {shift_type}
Total Amount: *Rs. {int(total_cost)}*
User Phone: {user_phone}
User CNIC: {user_cnic}

Please verify the payment by looking at the screenshot.

To confirm : confirm `{booking_id}`
To reject : reject `{booking_id}` [reason]
"""

        # Format customer notification message
        client_message = f"""📸 *Payment Screenshot Received!*

⏱️ *Verification Status:*
🔍 Under Review (Usually takes 5-10 minutes)
✅ You'll get confirmation message once verified

Thank you for your patience! 😊
"""
        
        # Send notification to customer
        notification_service = _get_notification_service()
        session_repo = SessionRepository()
        user_session = session_repo.get_by_user_id(db, booking.user_id)
        
        if user_session and user_session.source == "Website":
            # Website booking - save to user's chat
            notification_service.save_web_message(booking.user_id, client_message, sender="bot")
        elif user_phone:
            # WhatsApp booking - send via WhatsApp
            notification_service.send_whatsapp_message_sync(
                user_phone, 
                client_message, 
                booking.user.user_id, 
                save_to_db=True
            )
        else:
            # Fallback to web message
            notification_service.save_web_message(booking.user_id, client_message, sender="bot")
        
        return admin_message
        
    except Exception as e:
        print(f"❌ Error in process_payment_screenshot: {e}")
        return {"error": str(e)}
    finally:
        db.close()


@tool("process_payment_details")
def process_payment_details(
    session_id: str,
    booking_id: str,
    transaction_id: Optional[str] = None,
    sender_name: Optional[str] = None,
    amount: Optional[str] = None,
    sender_phone: Optional[str] = None
) -> dict:
    """
    Process manual payment details when user provides transaction info via text.
    Use when user gives payment information like:
    - "Transaction ID: TXN123456"
    - "I paid 5000 rupees"
    - "My transaction ID is ABC123"
    - Provides payment details in text format
    
    Args:
        session_id: Current session ID
        booking_id: Booking ID for payment
        transaction_id: Payment transaction/reference ID (optional)
        sender_name: Name of person who made payment
        amount: Amount paid
        sender_phone: Phone number of sender (optional)
        
    Returns:
        Verification status and next steps
    """
    db = SessionLocal()
    try:
        # Get payment service
        payment_service = _get_payment_service()
        
        # Process payment details using service
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
            # Mark state change for memory system
            from app.agents.memory.state_detector import mark_state_change
            session_repo = SessionRepository()
            booking_repo = BookingRepository()
            booking = booking_repo.get_by_booking_id(db, booking_id)
            
            if booking:
                user_session = session_repo.get_by_user_id(db, booking.user_id)
                if user_session:
                    mark_state_change(user_session.id, db)
            
            if booking:
                # Get property name
                property_name = booking.property.name if booking.property else "Unknown Property"
                
                # Format payment details for admin
                payment_details = result.get("payment_details", {})
                admin_message = f"""💳 *Payment Details Received!*

Booking ID: `{booking_id}`
Property: *{property_name}*
Date: {booking.booking_date.strftime("%d %B %Y")}
Shift: {booking.shift_type}
Amount: *Rs. {int(booking.total_cost)}*

*Payment Details:*
👤 Sender: {payment_details.get('sender_name', 'N/A')}
💰 Amount: Rs. {payment_details.get('amount', 'N/A')}
🆔 Transaction ID: {payment_details.get('transaction_id', 'Not provided')}
📱 Phone: {payment_details.get('sender_phone', 'Not provided')}
📞 EasyPaisa: {payment_details.get('receiver_phone', 'N/A')}

Please verify the payment details.

To confirm : confirm `{booking_id}`
To reject : reject `{booking_id}` [reason]
"""
                
                # Send to admin (this would be handled by notification service in production)
                # For now, we'll just log it
                print(f"📧 Admin notification: {admin_message}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error processing payment details: {e}")
        return {"error": "❌ Error processing payment details. Please try again or contact support."}
    finally:
        db.close()


@tool("confirm_booking_payment")
def confirm_booking_payment(booking_id: str) -> dict:
    """
    Confirm booking after admin verification (internal use).
    Admin Agent can call this tool to confirm a booking after verifying payment.
    Returns customer_phone and message for webhook to send to customer.
    
    Args:
        booking_id: The booking ID to confirm
        
    Returns:
        Confirmation status and customer notification
    """
    db = SessionLocal()
    try:
        # Get payment service
        payment_service = _get_payment_service()
        
        # Verify payment using service
        result = payment_service.verify_payment(
            db=db,
            booking_id=booking_id,
            verified_by="admin_agent"
        )
        
        if not result.get("success"):
            return result
        
        # Get booking details for notification
        booking = result.get("booking")
        if not booking:
            return {"error": "❌ Booking not found after confirmation"}
        
        # Format confirmation message for customer
        property_name = booking.property.name if booking.property else "Your Selected Property"
        property_address = booking.property.address if booking.property else "Address will be shared separately"
        property_contact = booking.property.contact_number if booking.property else "Contact details will be provided"
        
        formatted_date = booking.booking_date.strftime("%d %B %Y (%A)")
        
        confirmation_message = f"""🎉 *BOOKING CONFIRMED!* ✅

Congratulations! Your payment has been verified and your booking is now confirmed!

📋 *Booking Details:*
🆔 Booking ID: `{booking_id}`
🏠 Property: *{property_name}*
📍 Location: {property_address}
📅 Date: {formatted_date}
🕐 Shift: {booking.shift_type}
💰 Total Amount: Rs. {int(booking.total_cost)}

📞 *Property Contact:*
{property_contact}

🎊 *What's Next?*
• Save this confirmation message
• Arrive on time for your booking
• Contact property for any special requests
• Have a wonderful time!

Thank you for choosing us! 😊

_For any queries, feel free to message us._"""

        # Send notification to customer
        notification_service = _get_notification_service()
        session_repo = SessionRepository()
        user_session = session_repo.get_by_user_id(db, booking.user_id)
        
        if user_session and user_session.source == "Website":
            # Website booking
            notification_service.save_web_message(booking.user_id, confirmation_message, sender="bot")
        elif booking.user.phone_number:
            # WhatsApp booking
            notification_service.send_whatsapp_message_sync(
                booking.user.phone_number,
                confirmation_message,
                booking.user.user_id,
                save_to_db=True
            )
        else:
            # Fallback
            notification_service.save_web_message(booking.user_id, confirmation_message, sender="bot")
        
        # Return data for admin
        return {
            "success": True,
            "customer_phone": booking.user.phone_number,
            "customer_user_id": booking.user.user_id,
            "message": confirmation_message,
            "already_confirmed": result.get("already_confirmed", False)
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error confirming booking: {e}")
        return {"error": f"❌ Error confirming booking: {str(e)}"}
    finally:
        db.close()


@tool("reject_booking_payment")
def reject_booking_payment(booking_id: str, reason: str = None) -> dict:
    """
    Reject booking payment after admin review (internal use).
    This is called automatically when admin rejects payment.
    Make sure the reason is formatted and explained clearly.
    Returns customer_phone and message for webhook to send to customer.
    
    Args:
        booking_id: The booking ID to reject
        reason: Reason for rejection (e.g., amount_mismatch, transaction_not_found)
        
    Returns:
        Rejection status and customer notification
    """
    db = SessionLocal()
    try:
        # Validate reason
        if not reason or not reason.strip():
            return {"error": "❌ Rejection reason is required"}
        
        # Get payment service
        payment_service = _get_payment_service()
        
        # Reject payment using service
        result = payment_service.reject_payment(
            db=db,
            booking_id=booking_id,
            reason=reason,
            rejected_by="admin_agent"
        )
        
        if not result.get("success"):
            return result
        
        # Get booking details for notification
        booking = result.get("booking")
        if not booking:
            return {"error": "❌ Booking not found after rejection"}
        
        # Get property name
        property_name = booking.property.name if booking.property else "Your Property"
        
        # Format rejection message for customer
        from app.core.constants import EASYPAISA_NUMBER
        
        rejection_message = f"""❌ *PAYMENT VERIFICATION FAILED*

We couldn't verify your payment for:

📋 *Booking Details:*
🆔 Booking ID: `{booking.booking_id}`
🏠 Property: {property_name}
💰 Required Amount: Rs. {int(booking.total_cost)}

❌ *Issue Found:*
{reason}

━━━━━━━━━━━━━━━━━━━━━━━━━

💳 *TO COMPLETE YOUR BOOKING:*

1️⃣ *Make Correct Payment:*
   • Amount: Rs. {int(booking.total_cost)} (exact amount)
   • EasyPaisa: {EASYPAISA_NUMBER}
   • Account Name: HutBuddy

2️⃣ *Send Payment Proof:*
   • Clear screenshot of payment confirmation
   • Or provide: Your Name ✅, Amount ✅, Transaction ID ⚪ (optional)

━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ *Your booking is still RESERVED for 30 minutes*

Need help? Contact our support team or try the payment again.

_We're here to help you complete your booking!_ 😊"""
        
        # Send notification to customer
        notification_service = _get_notification_service()
        session_repo = SessionRepository()
        user_session = session_repo.get_by_user_id(db, booking.user_id)
        
        if user_session and user_session.source == "Website":
            # Website booking
            notification_service.save_web_message(booking.user_id, rejection_message, sender="bot")
        elif booking.user.phone_number:
            # WhatsApp booking
            notification_service.send_whatsapp_message_sync(
                booking.user.phone_number,
                rejection_message,
                booking.user.user_id,
                save_to_db=True
            )
        else:
            # Fallback
            notification_service.save_web_message(booking.user_id, rejection_message, sender="bot")
        
        # Return data for admin
        return {
            "success": True,
            "customer_phone": booking.user.phone_number,
            "customer_user_id": booking.user.user_id,
            "message": rejection_message,
            "booking_status": "Pending",
            "reason": reason
        }
        
    except Exception as e:
        print(f"❌ Error rejecting payment: {e}")
        return {"error": f"❌ Error rejecting payment: {str(e)}"}
    finally:
        db.close()


# Export tools list for agent registration
payment_tools = [
    process_payment_screenshot,
    process_payment_details,
    confirm_booking_payment,
    reject_booking_payment,
]

__all__ = [
    "process_payment_screenshot",
    "process_payment_details",
    "confirm_booking_payment",
    "reject_booking_payment",
    "payment_tools",
]
