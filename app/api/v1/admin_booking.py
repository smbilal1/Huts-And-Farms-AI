"""
Admin booking management API endpoints.

This module provides HTTP endpoints for admin operations on bookings,
including confirming and rejecting bookings with automatic user notifications.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.dependencies import (
    get_payment_service,
    get_notification_service,
    get_user_repository,
    get_session_repository,
    get_message_repository
)
from app.services.payment_service import PaymentService
from app.services.notification_service import NotificationService
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.booking_repository import BookingRepository
from app.integrations.whatsapp import WhatsAppClient
from app.core.exceptions import (
    AppException,
    BookingException,
    PaymentException
)

router = APIRouter(prefix="/admin/bookings", tags=["admin-bookings"])


# ==================== Request Models ====================

class ConfirmBookingRequest(BaseModel):
    """Request model for confirming a booking."""
    booking_id: str
    admin_notes: Optional[str] = None


class RejectBookingRequest(BaseModel):
    """Request model for rejecting a booking."""
    booking_id: str
    rejection_reason: str
    admin_notes: Optional[str] = None


# ==================== Response Models ====================

class BookingActionResponse(BaseModel):
    """Response model for booking actions."""
    success: bool
    message: str
    booking_id: str
    booking_status: str
    user_notified: bool
    notification_method: Optional[str] = None
    error: Optional[str] = None


# ==================== API Routes ====================

@router.post("/confirm", response_model=BookingActionResponse)
async def confirm_booking(
    request: ConfirmBookingRequest,
    db: Session = Depends(get_db),
    payment_service: PaymentService = Depends(get_payment_service),
    user_repo: UserRepository = Depends(get_user_repository),
    session_repo: SessionRepository = Depends(get_session_repository),
    message_repo: MessageRepository = Depends(get_message_repository)
):
    """
    Confirm a booking and notify the user.
    
    This endpoint:
    1. Verifies the booking exists and is in correct state
    2. Updates booking status to "Confirmed"
    3. Determines user's communication method (WhatsApp or Web)
    4. Sends confirmation message via appropriate channel
    5. Returns confirmation status
    
    Args:
        request: Booking confirmation request with booking_id and optional notes
        db: Database session
        payment_service: Payment service for booking confirmation
        user_repo: User repository
        session_repo: Session repository  
        message_repo: Message repository
        
    Returns:
        BookingActionResponse with confirmation status and user notification info
        
    Raises:
        HTTPException: If booking not found, invalid state, or notification fails
    """
    try:
        # Verify and confirm the booking
        result = payment_service.verify_payment(
            db=db,
            booking_id=request.booking_id,
            verified_by="admin_panel",
            verification_notes=request.admin_notes
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400, 
                detail=result.get("error", "Failed to confirm booking")
            )
        
        booking = result["booking"]
        customer_user_id = result["customer_user_id"]
        customer_phone = result.get("customer_phone")
        confirmation_message = result["message"]
        
        # Determine how to notify the user (WhatsApp or Web)
        user_session = session_repo.get_by_user_id(db, customer_user_id)
        notification_method = None
        user_notified = False
        
        if user_session and user_session.source == "Website":
            # Web user - save message to their chat
            message_repo.save_message(
                db=db,
                user_id=customer_user_id,
                sender="bot",
                content=confirmation_message,
                whatsapp_message_id=None
            )
            notification_method = "web_chat"
            user_notified = True
            
        elif user_session and user_session.source == "Chatbot" and customer_phone:
            # WhatsApp user - send via WhatsApp
            try:
                whatsapp_client = WhatsAppClient()
                whatsapp_result = await whatsapp_client.send_message(
                    customer_phone,
                    confirmation_message,
                    customer_user_id,
                    save_to_db=True
                )
                
                if whatsapp_result.get("success"):
                    notification_method = "whatsapp"
                    user_notified = True
                else:
                    # Fallback to web chat if WhatsApp fails
                    message_repo.save_message(
                        db=db,
                        user_id=customer_user_id,
                        sender="bot",
                        content=confirmation_message,
                        whatsapp_message_id=None
                    )
                    notification_method = "web_chat_fallback"
                    user_notified = True
                    
            except Exception as e:
                print(f"❌ WhatsApp notification failed: {e}")
                # Fallback to web chat
                message_repo.save_message(
                    db=db,
                    user_id=customer_user_id,
                    sender="bot",
                    content=confirmation_message,
                    whatsapp_message_id=None
                )
                notification_method = "web_chat_fallback"
                user_notified = True
        else:
            # Unknown source or no phone - fallback to web chat
            message_repo.save_message(
                db=db,
                user_id=customer_user_id,
                sender="bot",
                content=confirmation_message,
                whatsapp_message_id=None
            )
            notification_method = "web_chat_fallback"
            user_notified = True
        
        return BookingActionResponse(
            success=True,
            message=f"Booking {request.booking_id} confirmed successfully",
            booking_id=request.booking_id,
            booking_status="Confirmed",
            user_notified=user_notified,
            notification_method=notification_method
        )
        
    except HTTPException:
        raise
    except BookingException as e:
        print(f"❌ Booking error in confirm booking: {e}")
        raise HTTPException(status_code=400, detail=e.message)
    except PaymentException as e:
        print(f"❌ Payment error in confirm booking: {e}")
        raise HTTPException(status_code=400, detail=e.message)
    except AppException as e:
        print(f"❌ Application error in confirm booking: {e}")
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        import traceback
        print(f"❌ Unexpected error in confirm booking: {e}")
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while confirming the booking")


@router.post("/reject", response_model=BookingActionResponse)
async def reject_booking(
    request: RejectBookingRequest,
    db: Session = Depends(get_db),
    payment_service: PaymentService = Depends(get_payment_service),
    user_repo: UserRepository = Depends(get_user_repository),
    session_repo: SessionRepository = Depends(get_session_repository),
    message_repo: MessageRepository = Depends(get_message_repository)
):
    """
    Reject a booking and notify the user.
    
    This endpoint:
    1. Verifies the booking exists
    2. Updates booking status back to "Pending" (so user can retry)
    3. Determines user's communication method (WhatsApp or Web)
    4. Sends rejection message via appropriate channel
    5. Returns rejection status
    
    Args:
        request: Booking rejection request with booking_id, reason, and optional notes
        db: Database session
        payment_service: Payment service for booking rejection
        user_repo: User repository
        session_repo: Session repository
        message_repo: Message repository
        
    Returns:
        BookingActionResponse with rejection status and user notification info
        
    Raises:
        HTTPException: If booking not found or notification fails
    """
    try:
        # Reject the booking
        result = payment_service.reject_payment(
            db=db,
            booking_id=request.booking_id,
            reason=request.rejection_reason,
            rejected_by="admin_panel"
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to reject booking")
            )
        
        booking = result["booking"]
        customer_user_id = result["customer_user_id"]
        customer_phone = result.get("customer_phone")
        rejection_message = result["message"]
        
        # Determine how to notify the user (WhatsApp or Web)
        user_session = session_repo.get_by_user_id(db, customer_user_id)
        notification_method = None
        user_notified = False
        
        if user_session and user_session.source == "Website":
            # Web user - save message to their chat
            message_repo.save_message(
                db=db,
                user_id=customer_user_id,
                sender="bot",
                content=rejection_message,
                whatsapp_message_id=None
            )
            notification_method = "web_chat"
            user_notified = True
            
        elif user_session and user_session.source == "Chatbot" and customer_phone:
            # WhatsApp user - send via WhatsApp
            try:
                whatsapp_client = WhatsAppClient()
                whatsapp_result = await whatsapp_client.send_message(
                    customer_phone,
                    rejection_message,
                    customer_user_id,
                    save_to_db=True
                )
                
                if whatsapp_result.get("success"):
                    notification_method = "whatsapp"
                    user_notified = True
                else:
                    # Fallback to web chat if WhatsApp fails
                    message_repo.save_message(
                        db=db,
                        user_id=customer_user_id,
                        sender="bot",
                        content=rejection_message,
                        whatsapp_message_id=None
                    )
                    notification_method = "web_chat_fallback"
                    user_notified = True
                    
            except Exception as e:
                print(f"❌ WhatsApp notification failed: {e}")
                # Fallback to web chat
                message_repo.save_message(
                    db=db,
                    user_id=customer_user_id,
                    sender="bot",
                    content=rejection_message,
                    whatsapp_message_id=None
                )
                notification_method = "web_chat_fallback"
                user_notified = True
        else:
            # Unknown source or no phone - fallback to web chat
            message_repo.save_message(
                db=db,
                user_id=customer_user_id,
                sender="bot",
                content=rejection_message,
                whatsapp_message_id=None
            )
            notification_method = "web_chat_fallback"
            user_notified = True
        
        return BookingActionResponse(
            success=True,
            message=f"Booking {request.booking_id} rejected successfully",
            booking_id=request.booking_id,
            booking_status="Pending",
            user_notified=user_notified,
            notification_method=notification_method
        )
        
    except HTTPException:
        raise
    except BookingException as e:
        print(f"❌ Booking error in reject booking: {e}")
        raise HTTPException(status_code=400, detail=e.message)
    except PaymentException as e:
        print(f"❌ Payment error in reject booking: {e}")
        raise HTTPException(status_code=400, detail=e.message)
    except AppException as e:
        print(f"❌ Application error in reject booking: {e}")
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        import traceback
        print(f"❌ Unexpected error in reject booking: {e}")
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while rejecting the booking")


@router.get("/status/{booking_id}")
async def get_booking_status(
    booking_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the current status of a booking.
    
    Args:
        booking_id: Unique booking identifier
        db: Database session
        
    Returns:
        Dict with booking status information
        
    Raises:
        HTTPException: If booking not found
    """
    try:
        booking_repo = BookingRepository()
        booking = booking_repo.get_by_booking_id(db, booking_id)
        
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        return {
            "booking_id": booking.booking_id,
            "status": booking.status,
            "user_id": str(booking.user_id),
            "property_name": booking.property.name,
            "booking_date": booking.booking_date.isoformat(),
            "shift_type": booking.shift_type,
            "total_cost": float(booking.total_cost),
            "payment_screenshot_url": booking.payment_screenshot_url,
            "created_at": booking.created_at.isoformat() if booking.created_at else None,
            "updated_at": booking.updated_at.isoformat() if booking.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting booking status: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching booking status")