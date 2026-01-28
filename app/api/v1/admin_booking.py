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
    get_user_repository,
    get_message_repository
)
from app.services.payment_service import PaymentService
from app.repositories.user_repository import UserRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.booking_repository import BookingRepository
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


class UpdateBookingStatusRequest(BaseModel):
    """Request model for updating booking status."""
    booking_id: str
    status: str  # "Pending", "Waiting", "Confirmed", "Cancelled", "Completed", "Expired"
    admin_notes: Optional[str] = None
    rejection_reason: Optional[str] = None  # Required only for "Cancelled" status


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
        
        # Get customer info from the booking - with fallback to result data
        customer_user_id = booking.user_id
        customer_phone = None
        
        # Try to get phone from user relationship first
        if hasattr(booking, 'user') and booking.user:
            customer_phone = booking.user.phone_number
        
        # Fallback to result data if available
        if not customer_phone and "customer_phone" in result:
            customer_phone = result["customer_phone"]
            
        confirmation_message = result["message"]
        
        # Send confirmation message via web chat only
        message_repo.save_message(
            db=db,
            user_id=customer_user_id,
            sender="bot",
            content=confirmation_message,
            whatsapp_message_id=None
        )
        
        return BookingActionResponse(
            success=True,
            message=f"Booking {request.booking_id} confirmed successfully",
            booking_id=request.booking_id,
            booking_status="Confirmed",
            user_notified=True,
            notification_method="web_chat"
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
        
        # Get customer info from the booking - with fallback to result data
        customer_user_id = booking.user_id
        customer_phone = None
        
        # Try to get phone from user relationship first
        if hasattr(booking, 'user') and booking.user:
            customer_phone = booking.user.phone_number
        
        # Fallback to result data if available
        if not customer_phone and "customer_phone" in result:
            customer_phone = result["customer_phone"]
            
        rejection_message = result["message"]
        
        # Send rejection message via web chat only
        message_repo.save_message(
            db=db,
            user_id=customer_user_id,
            sender="bot",
            content=rejection_message,
            whatsapp_message_id=None
        )
        
        return BookingActionResponse(
            success=True,
            message=f"Booking {request.booking_id} rejected successfully",
            booking_id=request.booking_id,
            booking_status="Pending",
            user_notified=True,
            notification_method="web_chat"
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


@router.post("/update-status", response_model=BookingActionResponse)
async def update_booking_status(
    request: UpdateBookingStatusRequest,
    db: Session = Depends(get_db),
    payment_service: PaymentService = Depends(get_payment_service),
    message_repo: MessageRepository = Depends(get_message_repository)
):
    """
    Update booking status with optional user notification.
    
    This endpoint:
    1. Updates booking status to the specified value
    2. Sends user notification ONLY for "Confirmed" and "Cancelled" status
    3. No notification for "Pending", "Waiting", "Completed", "Expired"
    4. Returns update status
    
    Args:
        request: Status update request with booking_id, status, and optional notes
        db: Database session
        payment_service: Payment service for status updates
        message_repo: Message repository for notifications
        
    Returns:
        BookingActionResponse with update status and notification info
        
    Raises:
        HTTPException: If booking not found or invalid status
    """
    try:
        booking_repo = BookingRepository()
        
        # Validate status
        valid_statuses = ["Pending", "Waiting", "Confirmed", "Cancelled", "Completed", "Expired"]
        if request.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Get booking
        booking = booking_repo.get_by_booking_id(db, request.booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        customer_user_id = booking.user_id
        user_notified = False
        notification_method = None
        message_content = None
        
        # Handle different status updates
        if request.status == "Confirmed":
            # Use payment service for confirmation (includes proper message formatting)
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
            
            message_content = result["message"]
            user_notified = True
            notification_method = "web_chat"
            
        elif request.status == "Cancelled":
            # Use payment service for rejection (includes proper message formatting)
            rejection_reason = request.rejection_reason or "Booking cancelled by admin"
            
            result = payment_service.reject_payment(
                db=db,
                booking_id=request.booking_id,
                reason=rejection_reason,
                rejected_by="admin_panel"
            )
            
            if not result["success"]:
                raise HTTPException(
                    status_code=400,
                    detail=result.get("error", "Failed to cancel booking")
                )
            
            message_content = result["message"]
            user_notified = True
            notification_method = "web_chat"
            
        else:
            # For other statuses (Pending, Waiting, Completed, Expired) - just update status
            booking = booking_repo.update_status(db, request.booking_id, request.status)
            if not booking:
                raise HTTPException(status_code=404, detail="Failed to update booking status")
        
        # Send notification message if needed
        if user_notified and message_content:
            message_repo.save_message(
                db=db,
                user_id=customer_user_id,
                sender="bot",
                content=message_content,
                whatsapp_message_id=None
            )
        
        return BookingActionResponse(
            success=True,
            message=f"Booking {request.booking_id} status updated to {request.status}",
            booking_id=request.booking_id,
            booking_status=request.status,
            user_notified=user_notified,
            notification_method=notification_method
        )
        
    except HTTPException:
        raise
    except BookingException as e:
        print(f"❌ Booking error in update status: {e}")
        raise HTTPException(status_code=400, detail=e.message)
    except PaymentException as e:
        print(f"❌ Payment error in update status: {e}")
        raise HTTPException(status_code=400, detail=e.message)
    except AppException as e:
        print(f"❌ Application error in update status: {e}")
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        import traceback
        print(f"❌ Unexpected error in update status: {e}")
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while updating booking status")


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