"""
Admin API endpoints.

This module provides HTTP endpoints for admin functionality including
payment verification notifications and admin command processing.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
import re

from app.database import get_db
from app.api.dependencies import (
    get_message_repository,
    get_session_service,
    get_notification_service,
    get_booking_repository,
    get_user_repository
)
from app.repositories.message_repository import MessageRepository
from app.repositories.booking_repository import BookingRepository
from app.repositories.user_repository import UserRepository
from app.services.session_service import SessionService
from app.services.notification_service import NotificationService
from app.agents.admin_agent import AdminAgent
from app.core.constants import WEB_ADMIN_USER_ID
from app.core.exceptions import (
    AppException,
    BookingException,
    PaymentException,
    PropertyException,
    IntegrationException
)
from app.models.user import Session as SessionModel
from app.models.message import Message


router = APIRouter(prefix="/web-chat/admin", tags=["admin"])

# Admin agent will be initialized lazily to avoid import-time dependencies
_admin_agent = None


def get_admin_agent() -> AdminAgent:
    """
    Get or create admin agent instance.
    
    Returns:
        AdminAgent: Admin agent instance
    """
    global _admin_agent
    if _admin_agent is None:
        _admin_agent = AdminAgent()
    return _admin_agent


# ==================== Request Models ====================

class AdminMessageRequest(BaseModel):
    """Request model for admin messages."""
    message: str
    admin_user_id: str


# ==================== Response Models ====================

class AdminNotification(BaseModel):
    """Response model for admin notifications."""
    message_id: int
    content: str
    timestamp: datetime
    is_read: bool = False


class AdminNotificationsResponse(BaseModel):
    """Response model for admin notifications list."""
    status: str
    notifications: List[AdminNotification]
    count: int


class AdminMessageResponse(BaseModel):
    """Response model for admin message operations."""
    status: str
    bot_response: Optional[str] = None
    message_id: Optional[int] = None
    error: Optional[str] = None


# ==================== Helper Functions ====================

def validate_admin_user(user_id_str: str, user_repo: UserRepository, db: Session) -> UUID:
    """
    Validate that the user is an admin.
    
    Args:
        user_id_str: User ID as string
        user_repo: User repository instance
        db: Database session
        
    Returns:
        UUID: Validated admin user ID
        
    Raises:
        HTTPException: If user is not found or not an admin
    """
    try:
        user_id_uuid = UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    # Verify user exists
    user = user_repo.get_by_id(db, user_id_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify user is admin
    if user_id_uuid != WEB_ADMIN_USER_ID:
        raise HTTPException(status_code=403, detail="Access denied: Admin privileges required")
    
    return user_id_uuid


def extract_booking_id_from_response(response_text: str) -> Optional[str]:
    """
    Extract booking ID from agent response.
    
    Args:
        response_text: Agent response text
        
    Returns:
        Optional[str]: Extracted booking ID or None
    """
    # Try to extract booking ID pattern: `Name-Date-Shift` or Booking ID: `Name-Date-Shift`
    booking_id_pattern = r'Booking ID: `([^`]+)`|`([A-Za-z\s]+-\d{4}-\d{2}-\d{2}-[A-Za-z\s]+)`'
    match = re.search(booking_id_pattern, response_text)
    if match:
        return match.group(1) or match.group(2)
    return None


async def route_customer_notification(
    booking_id: str,
    customer_message: str,
    db: Session,
    notification_service: NotificationService,
    message_repo: MessageRepository
) -> str:
    """
    Route notification to customer based on their session source.
    
    Args:
        booking_id: Booking ID
        customer_message: Message to send to customer
        db: Database session
        notification_service: Notification service instance
        message_repo: Message repository instance
        
    Returns:
        str: Admin feedback message
    """
    from app.models.booking import Booking
    
    # Find booking
    booking = db.query(Booking).filter_by(booking_id=booking_id).first()
    
    if not booking:
        print(f"❌ Booking not found: {booking_id}")
        return f"❌ Booking not found: {booking_id}"
    
    customer_user_id = booking.user_id
    customer_phone = booking.user.phone_number
    
    print(f"✅ Found booking:")
    print(f"   Booking ID: {booking_id}")
    print(f"   Customer User ID: {customer_user_id}")
    print(f"   Customer Phone: {customer_phone}")
    
    # Get customer's session to check source
    customer_session = db.query(SessionModel).filter_by(user_id=customer_user_id).first()
    
    if not customer_session:
        print(f"❌ No session found for customer: {customer_user_id}")
        return f"❌ Customer session not found for booking: {booking_id}"
    
    # Route based on session source
    if customer_session.source == "Website":
        # Website customer - save to their chat
        message_repo.save_message(
            db=db,
            user_id=customer_user_id,
            content=customer_message,
            sender="bot"
        )
        print(f"📧 Sent confirmation to website customer: {customer_user_id}")
        return f"✅ Confirmation sent to website customer\nBooking: {booking_id}"
    
    elif customer_session.source == "Chatbot":
        # Chatbot (WhatsApp) customer - send via WhatsApp
        if customer_phone:
            result = await notification_service._send_to_whatsapp_user(
                db=db,
                phone_number=customer_phone,
                user_id=customer_user_id,
                message=customer_message
            )
            if result.get("success"):
                print(f"📱 Sent confirmation to chatbot customer: {customer_phone}")
                return f"✅ Confirmation sent to chatbot customer via WhatsApp\nBooking: {booking_id}\nPhone: {customer_phone}"
            else:
                print(f"❌ WhatsApp send failed for: {customer_phone}")
                return f"❌ Failed to send WhatsApp message\nBooking: {booking_id}\nPhone: {customer_phone}"
        else:
            print(f"❌ No phone number for chatbot customer: {customer_user_id}")
            return f"❌ Chatbot customer has no phone number\nBooking: {booking_id}"
    
    else:
        # Unknown source - fallback
        print(f"⚠️ Unknown session source: {customer_session.source}")
        is_web_customer = not customer_phone or customer_phone == ""
        
        if is_web_customer:
            message_repo.save_message(
                db=db,
                user_id=customer_user_id,
                content=customer_message,
                sender="bot"
            )
            return f"✅ Confirmation sent (fallback to web)\nBooking: {booking_id}"
        else:
            await notification_service._send_to_whatsapp_user(
                db=db,
                phone_number=customer_phone,
                user_id=customer_user_id,
                message=customer_message
            )
            return f"✅ Confirmation sent (fallback to WhatsApp)\nBooking: {booking_id}"


# ==================== API Routes ====================

@router.get("/notifications", response_model=AdminNotificationsResponse)
async def get_admin_notifications(
    db: Session = Depends(get_db),
    message_repo: MessageRepository = Depends(get_message_repository)
):
    """
    Get pending payment verification requests for admin.
    
    Returns messages sent to admin that contain payment verification requests.
    
    Returns:
        AdminNotificationsResponse: List of admin notifications
    """
    try:
        # Get recent messages for admin user that contain verification requests
        admin_messages = message_repo.get_messages_by_filter(
            db=db,
            user_id=WEB_ADMIN_USER_ID,
            sender="bot",
            content_filter="%PAYMENT VERIFICATION REQUEST%",
            limit=20
        )
        
        notifications = [
            AdminNotification(
                message_id=msg.id,
                content=msg.content,
                timestamp=msg.timestamp,
                is_read=False
            )
            for msg in admin_messages
        ]
        
        return AdminNotificationsResponse(
            status="success",
            notifications=notifications,
            count=len(notifications)
        )
        
    except AppException as e:
        print(f"❌ Application error fetching admin notifications: {e}")
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        print(f"❌ Unexpected error fetching admin notifications: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching notifications")


@router.post("/send-message", response_model=AdminMessageResponse)
async def send_admin_message(
    message_data: AdminMessageRequest,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
    session_service: SessionService = Depends(get_session_service),
    notification_service: NotificationService = Depends(get_notification_service),
    message_repo: MessageRepository = Depends(get_message_repository)
):
    """
    Process admin confirmation/rejection commands.
    
    Handles admin messages like "confirm ABC-123" or "reject ABC-123" and routes
    notifications to customers based on their session source (Website or WhatsApp).
    
    Args:
        message_data: Admin message request
        db: Database session
        user_repo: User repository
        session_service: Session service
        notification_service: Notification service
        message_repo: Message repository
        
    Returns:
        AdminMessageResponse: Response with status and admin feedback
    """
    try:
        # Validate admin user
        admin_user_id = validate_admin_user(message_data.admin_user_id, user_repo, db)
        incoming_text = message_data.message
        
        print(f"🔑 Processing admin command from user: {admin_user_id}")
        print(f"📝 Command: {incoming_text}")
        
        # Get or create admin session
        session_result = session_service.get_or_create_session(
            db=db,
            user_id=admin_user_id,
            session_id=str(admin_user_id),  # Use admin user ID as session ID
            source="Website"
        )
        session_id = session_result.get("session_id") if isinstance(session_result, dict) else session_result
        print(f"📋 Admin session ID: {session_id}")
        
        # Save admin's message
        admin_message = message_repo.save_message(
            db=db,
            user_id=admin_user_id,
            content=incoming_text,
            sender="admin"
        )
        print(f"✅ Admin message saved - ID: {admin_message.id}")
        
        # Call admin agent to process the command
        admin_agent = get_admin_agent()
        agent_response = admin_agent.get_response(incoming_text, session_id)
        print(f"🤖 Admin agent response: {agent_response}")
        
        # Extract booking ID from response
        response_text = str(agent_response)
        booking_id_match = extract_booking_id_from_response(response_text)
        
        if booking_id_match:
            print(f"📋 Extracted booking ID: {booking_id_match}")
        
        # Handle agent response
        if isinstance(agent_response, dict):
            # Success case with customer notification
            if agent_response.get("success") and (agent_response.get("customer_phone") or booking_id_match):
                customer_message = agent_response.get("message", str(agent_response))
                
                # Route notification to customer
                if booking_id_match:
                    admin_feedback = await route_customer_notification(
                        booking_id=booking_id_match,
                        customer_message=customer_message,
                        db=db,
                        notification_service=notification_service,
                        message_repo=message_repo
                    )
                else:
                    # Fallback to old logic using customer_user_id from response
                    customer_user_id = agent_response.get("customer_user_id")
                    customer_phone = agent_response.get("customer_phone")
                    
                    if not customer_user_id:
                        admin_feedback = "❌ Could not identify customer"
                        print(f"❌ No customer_user_id or booking_id found")
                    else:
                        customer_session = db.query(SessionModel).filter_by(user_id=customer_user_id).first()
                        
                        if not customer_session:
                            admin_feedback = "❌ Customer session not found"
                        elif customer_session.source == "Website":
                            message_repo.save_message(
                                db=db,
                                user_id=customer_user_id,
                                content=customer_message,
                                sender="bot"
                            )
                            admin_feedback = "✅ Confirmation sent to website customer"
                        elif customer_session.source == "Chatbot":
                            await notification_service._send_to_whatsapp_user(
                                db=db,
                                phone_number=customer_phone,
                                user_id=customer_user_id,
                                message=customer_message
                            )
                            admin_feedback = "✅ Confirmation sent to chatbot customer"
                        else:
                            admin_feedback = "❌ Unknown customer type"
                
                # Save admin feedback to admin's chat
                admin_bot_message = message_repo.save_message(
                    db=db,
                    user_id=admin_user_id,
                    content=admin_feedback,
                    sender="bot"
                )
                
                return AdminMessageResponse(
                    status="success",
                    bot_response=admin_feedback,
                    message_id=admin_bot_message.id
                )
            
            # Error case
            elif agent_response.get("error"):
                error_msg = agent_response.get("error")
                
                # Save error to admin's chat
                admin_bot_message = message_repo.save_message(
                    db=db,
                    user_id=admin_user_id,
                    content=error_msg,
                    sender="bot"
                )
                
                return AdminMessageResponse(
                    status="error",
                    error=error_msg,
                    message_id=admin_bot_message.id
                )
        
        # Regular admin bot response (not a confirmation/rejection)
        admin_response_text = str(agent_response)
        
        # Save admin bot response
        admin_bot_message = message_repo.save_message(
            db=db,
            user_id=admin_user_id,
            content=admin_response_text,
            sender="bot"
        )
        
        return AdminMessageResponse(
            status="success",
            bot_response=admin_response_text,
            message_id=admin_bot_message.id
        )
        
    except HTTPException:
        raise
    except BookingException as e:
        print(f"❌ Booking error in admin message: {e}")
        raise HTTPException(status_code=400, detail=e.message)
    except PaymentException as e:
        print(f"❌ Payment error in admin message: {e}")
        raise HTTPException(status_code=400, detail=e.message)
    except IntegrationException as e:
        print(f"❌ Integration error in admin message: {e}")
        raise HTTPException(status_code=502, detail=f"External service error: {e.message}")
    except AppException as e:
        print(f"❌ Application error in admin message: {e}")
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        print(f"❌ Unexpected error in send_admin_message: {e}")
        print(f"   User ID: {message_data.admin_user_id}")
        print(f"   Command: {message_data.message}")
        import traceback
        print("❌ Full traceback:", traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the admin command"
        )
