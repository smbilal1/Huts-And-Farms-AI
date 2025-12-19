"""
Web chat API endpoints.

This module provides HTTP endpoints for web-based chat functionality including
message sending, image uploads, chat history, and session management.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.dependencies import (
    get_session_service,
    get_message_repository,
    get_payment_service,
    get_media_service,
    get_user_repository,
    get_session_repository
)
from app.services.session_service import SessionService
from app.services.payment_service import PaymentService
from app.services.media_service import MediaService
from app.repositories.message_repository import MessageRepository
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.agents.booking_agent import BookingToolAgent
from app.agents.admin_agent import AdminAgent
from app.core.constants import WEB_ADMIN_USER_ID
from app.core.exceptions import (
    AppException,
    BookingException,
    PaymentException,
    PropertyException,
    IntegrationException
)
from app.utils.formatters import formatting
from app.utils.media_utils import extract_media_urls, remove_cloudinary_links
from app.models.user import Session as SessionModel
from app.models.booking import Booking


router = APIRouter(prefix="/web-chat", tags=["web-chat"])

# Lazy initialization - agents will be created when first needed
_booking_agent = None
_admin_agent = None

def get_booking_agent():
    """Get or create the booking agent instance."""
    global _booking_agent
    if _booking_agent is None:
        _booking_agent = BookingToolAgent()
    return _booking_agent

def get_admin_agent():
    """Get or create the admin agent instance."""
    global _admin_agent
    if _admin_agent is None:
        _admin_agent = AdminAgent()
    return _admin_agent


# ==================== Request Models ====================

class WebChatMessage(BaseModel):
    """Request model for text messages."""
    message: str
    user_id: str


class WebImageMessage(BaseModel):
    """Request model for image messages."""
    image_data: str  # Base64 encoded image data OR Cloudinary URL
    user_id: str
    is_base64: bool = True  # True if image_data is base64, False if it's already a URL


class ChatHistoryRequest(BaseModel):
    """Request model for chat history retrieval."""
    user_id: str
    limit: Optional[int] = 50


# ==================== Response Models ====================

class MessageResponse(BaseModel):
    """Response model for individual messages."""
    message_id: int
    content: str
    sender: str
    timestamp: datetime
    media_urls: Optional[Dict[str, List[str]]] = None


class ChatResponse(BaseModel):
    """Response model for chat operations."""
    status: str
    bot_response: Optional[str] = None
    media_urls: Optional[Dict[str, List[str]]] = None
    message_id: Optional[int] = None
    error: Optional[str] = None


# ==================== Helper Functions ====================

def validate_and_get_user_id(user_id_str: str, user_repo: UserRepository, db: Session) -> UUID:
    """
    Validate user ID format and check if user exists.
    
    Args:
        user_id_str: User ID as string
        user_repo: User repository instance
        db: Database session
        
    Returns:
        UUID: Validated user ID
        
    Raises:
        HTTPException: If user ID is invalid or user not found
    """
    try:
        user_id_uuid = UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    user = user_repo.get_by_id(db, user_id_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_id_uuid


async def handle_admin_message(
    incoming_text: str,
    admin_user_id: UUID,
    db: Session,
    message_repo: MessageRepository,
    session_repo: SessionRepository
) -> ChatResponse:
    """
    Process admin confirmation/rejection commands.
    
    Args:
        incoming_text: Admin's message (e.g., "confirm ABC-123")
        admin_user_id: Admin's user ID
        db: Database session
        message_repo: Message repository
        session_repo: Session repository
        
    Returns:
        ChatResponse with status and admin feedback
    """
    try:
        # Get or create admin session
        admin_session = session_repo.create_or_get(
            db=db,
            user_id=admin_user_id,
            session_id=str(admin_user_id),
            source="Website"
        )
        
        # Save admin's message
        message_repo.save_message(
            db=db,
            user_id=admin_user_id,
            sender="admin",
            content=incoming_text,
            whatsapp_message_id=None
        )
        
        # Call admin agent to process the command
        admin_agent = get_admin_agent()
        agent_response = admin_agent.get_response(incoming_text, admin_session.id)
        
        # Extract booking ID from response if present
        import re
        booking_id_match = None
        response_text = str(agent_response)
        
        booking_id_pattern = r'Booking ID: `([^`]+)`|`([A-Za-z\s]+-\d{4}-\d{2}-\d{2}-[A-Za-z\s]+)`'
        match = re.search(booking_id_pattern, response_text)
        if match:
            booking_id_match = match.group(1) or match.group(2)
        
        # Handle agent response
        if isinstance(agent_response, dict):
            if agent_response.get("success") and (agent_response.get("customer_phone") or booking_id_match):
                # Get customer message
                customer_message = agent_response.get("message", str(agent_response))
                
                # If we have booking_id, use it to find the customer
                if booking_id_match:
                    booking = db.query(Booking).filter_by(booking_id=booking_id_match).first()
                    
                    if not booking:
                        admin_feedback = f"❌ Booking not found: {booking_id_match}"
                    else:
                        customer_user_id = booking.user_id
                        customer_phone = booking.user.phone_number
                        
                        # Get customer's session to check source
                        customer_session = session_repo.get_by_user_id(db, customer_user_id)
                        
                        if not customer_session:
                            admin_feedback = f"❌ Customer session not found for booking: {booking_id_match}"
                        elif customer_session.source == "Website":
                            # Website customer - save to their chat
                            message_repo.save_message(
                                db=db,
                                user_id=customer_user_id,
                                sender="bot",
                                content=customer_message,
                                whatsapp_message_id=None
                            )
                            admin_feedback = f"✅ Confirmation sent to website customer\nBooking: {booking_id_match}"
                        elif customer_session.source == "Chatbot":
                            # Chatbot (WhatsApp) customer - send via WhatsApp
                            if customer_phone:
                                from app.integrations.whatsapp import WhatsAppClient
                                whatsapp_client = WhatsAppClient()
                                result = await whatsapp_client.send_message(
                                    customer_phone,
                                    customer_message,
                                    customer_user_id,
                                    save_to_db=True
                                )
                                if result["success"]:
                                    admin_feedback = f"✅ Confirmation sent to chatbot customer via WhatsApp\nBooking: {booking_id_match}\nPhone: {customer_phone}"
                                else:
                                    admin_feedback = f"❌ Failed to send WhatsApp message\nBooking: {booking_id_match}\nPhone: {customer_phone}"
                            else:
                                admin_feedback = f"❌ Chatbot customer has no phone number\nBooking: {booking_id_match}"
                        else:
                            # Unknown source - fallback
                            is_web_customer = not customer_phone or customer_phone == ""
                            if is_web_customer:
                                message_repo.save_message(
                                    db=db,
                                    user_id=customer_user_id,
                                    sender="bot",
                                    content=customer_message,
                                    whatsapp_message_id=None
                                )
                                admin_feedback = f"✅ Confirmation sent (fallback to web)\nBooking: {booking_id_match}"
                            else:
                                from app.integrations.whatsapp import WhatsAppClient
                                whatsapp_client = WhatsAppClient()
                                await whatsapp_client.send_message(
                                    customer_phone,
                                    customer_message,
                                    customer_user_id,
                                    save_to_db=True
                                )
                                admin_feedback = f"✅ Confirmation sent (fallback to WhatsApp)\nBooking: {booking_id_match}"
                else:
                    # Fallback to old logic using customer_user_id from response
                    customer_user_id = agent_response.get("customer_user_id")
                    customer_phone = agent_response.get("customer_phone")
                    
                    if not customer_user_id:
                        admin_feedback = "❌ Could not identify customer"
                    else:
                        customer_session = session_repo.get_by_user_id(db, customer_user_id)
                        
                        if not customer_session:
                            admin_feedback = "❌ Customer session not found"
                        elif customer_session.source == "Website":
                            message_repo.save_message(
                                db=db,
                                user_id=customer_user_id,
                                sender="bot",
                                content=customer_message,
                                whatsapp_message_id=None
                            )
                            admin_feedback = "✅ Confirmation sent to website customer"
                        elif customer_session.source == "Chatbot":
                            from app.integrations.whatsapp import WhatsAppClient
                            whatsapp_client = WhatsAppClient()
                            await whatsapp_client.send_message(
                                customer_phone,
                                customer_message,
                                customer_user_id,
                                save_to_db=True
                            )
                            admin_feedback = "✅ Confirmation sent to chatbot customer"
                        else:
                            admin_feedback = "❌ Unknown customer type"
                
                # Save admin feedback to admin's chat
                admin_bot_message = message_repo.save_message(
                    db=db,
                    user_id=admin_user_id,
                    sender="bot",
                    content=admin_feedback,
                    whatsapp_message_id=None
                )
                
                return ChatResponse(
                    status="success",
                    bot_response=admin_feedback,
                    message_id=admin_bot_message.id
                )
            elif agent_response.get("error"):
                error_msg = agent_response.get("error")
                
                # Save error to admin's chat
                admin_bot_message = message_repo.save_message(
                    db=db,
                    user_id=admin_user_id,
                    sender="bot",
                    content=error_msg,
                    whatsapp_message_id=None
                )
                
                return ChatResponse(
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
            sender="bot",
            content=admin_response_text,
            whatsapp_message_id=None
        )
        
        return ChatResponse(
            status="success",
            bot_response=admin_response_text,
            message_id=admin_bot_message.id
        )
        
    except Exception as e:
        import traceback
        print(f"❌ Error in handle_admin_message: {e}")
        print(f"❌ Full traceback: {traceback.format_exc()}")
        
        return ChatResponse(
            status="error",
            error=f"Failed to process admin command: {str(e)}"
        )


# ==================== API Routes ====================

@router.post("/send-message", response_model=ChatResponse)
async def send_web_message(
    message_data: WebChatMessage,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
    session_service: SessionService = Depends(get_session_service),
    message_repo: MessageRepository = Depends(get_message_repository),
    session_repo: SessionRepository = Depends(get_session_repository)
):
    """
    Handle text messages from web chat.
    Routes to admin agent if sender is admin, otherwise to booking agent.
    
    Args:
        message_data: Message content and user ID
        db: Database session
        user_repo: User repository
        session_service: Session service
        message_repo: Message repository
        session_repo: Session repository
        
    Returns:
        ChatResponse with bot response and status
    """
    try:
        # Validate user
        user_id = validate_and_get_user_id(message_data.user_id, user_repo, db)
        incoming_text = message_data.message
        
        # Check if this is an admin user
        admin_uuid = WEB_ADMIN_USER_ID if isinstance(WEB_ADMIN_USER_ID, UUID) else UUID(WEB_ADMIN_USER_ID)
        if user_id == admin_uuid:
            return await handle_admin_message(
                incoming_text,
                user_id,
                db,
                message_repo,
                session_repo
            )
        
        # Regular user flow - continue with booking agent
        # Get or create session
        session_result = session_service.get_or_create_session(
            db=db,
            user_id=user_id,
            session_id=str(user_id),
            source="Website"
        )
        
        if not session_result["success"]:
            return ChatResponse(
                status="error",
                error=session_result.get("message", "Failed to create session")
            )
        
        session_id = session_result["session_id"]
        
        # Get bot response
        booking_agent = get_booking_agent()
        agent_response = booking_agent.get_response(
            incoming_text=incoming_text,
            session_id=session_id,
            whatsapp_message_id=None  # Not applicable for web
        )
        
        # Extract response content
        if isinstance(agent_response, dict):
            if 'output' in agent_response and isinstance(agent_response['output'], dict):
                message_content = agent_response['output'].get('message', '')
                error_content = agent_response['output'].get('error', '')
                response_text = message_content or error_content or str(agent_response)
            else:
                response_text = agent_response.get('message', '') or agent_response.get('error', '') or str(agent_response)
        else:
            response_text = str(agent_response)
        
        # Format response
        formatted_response = formatting(response_text)
        urls = extract_media_urls(formatted_response)
        
        # Prepare final message content
        if urls:
            cleaned_response = remove_cloudinary_links(formatted_response)
            final_message_content = cleaned_response
        else:
            final_message_content = formatted_response
        
        # Save bot message
        bot_message = message_repo.save_message(
            db=db,
            user_id=user_id,
            sender="bot",
            content=final_message_content,
            whatsapp_message_id=None
        )
        
        return ChatResponse(
            status="success",
            bot_response=final_message_content,
            media_urls=urls,
            message_id=bot_message.id
        )
        
    except HTTPException:
        raise
    except BookingException as e:
        print(f"❌ Booking error in web chat: {e}")
        raise HTTPException(status_code=400, detail=e.message)
    except PaymentException as e:
        print(f"❌ Payment error in web chat: {e}")
        raise HTTPException(status_code=400, detail=e.message)
    except PropertyException as e:
        print(f"❌ Property error in web chat: {e}")
        raise HTTPException(status_code=404, detail=e.message)
    except IntegrationException as e:
        print(f"❌ Integration error in web chat: {e}")
        raise HTTPException(status_code=502, detail=f"External service error: {e.message}")
    except AppException as e:
        print(f"❌ Application error in web chat: {e}")
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        import traceback
        print(f"❌ Unexpected error in web chat: {e}")
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.post("/send-image", response_model=ChatResponse)
async def send_web_image(
    image_data: WebImageMessage,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
    session_service: SessionService = Depends(get_session_service),
    message_repo: MessageRepository = Depends(get_message_repository),
    payment_service: PaymentService = Depends(get_payment_service),
    media_service: MediaService = Depends(get_media_service),
    session_repo: SessionRepository = Depends(get_session_repository)
):
    """
    Handle image messages from web chat.
    Accepts either base64 image data (uploads to Cloudinary) or Cloudinary URL.
    
    Args:
        image_data: Image data and user ID
        db: Database session
        user_repo: User repository
        session_service: Session service
        message_repo: Message repository
        payment_service: Payment service
        media_service: Media service
        session_repo: Session repository
        
    Returns:
        ChatResponse with processing status
    """
    try:
        # Validate user
        user_id = validate_and_get_user_id(image_data.user_id, user_repo, db)
        
        # Get session
        session = session_repo.get_by_user_id(db, user_id)
        
        if not session:
            error_message = "Please first complete your booking by selecting a farmhouse/hut. After booking confirmation, then send me your payment screenshot."
            
            # Save error message
            message_repo.save_message(
                db=db,
                user_id=user_id,
                sender="bot",
                content=error_message,
                whatsapp_message_id=None
            )
            
            return ChatResponse(
                status="no_booking_required",
                bot_response=error_message
            )
        
        booking_id = session.booking_id
        
        # Check if booking exists
        if booking_id is None:
            error_message = "Please first complete your booking by selecting a farmhouse/hut. After booking confirmation, then send me your payment screenshot."
            
            # Save error message
            message_repo.save_message(
                db=db,
                user_id=user_id,
                sender="bot",
                content=error_message,
                whatsapp_message_id=None
            )
            
            return ChatResponse(
                status="no_booking_required",
                bot_response=error_message
            )
        
        # Upload to Cloudinary if base64, otherwise use provided URL
        if image_data.is_base64:
            upload_result = await media_service.upload_image(
                image_data=image_data.image_data,
                folder="payment_screenshots"
            )
            
            if not upload_result["success"]:
                return ChatResponse(
                    status="error",
                    error="Failed to upload image. Please try again."
                )
            
            image_url = upload_result["url"]
        else:
            # Use provided Cloudinary URL
            image_url = image_data.image_data
        
        # Process payment screenshot
        result = await payment_service.process_payment_screenshot(
            db=db,
            booking_id=booking_id,
            image_data=image_url,
            is_base64=False  # Already uploaded
        )
        
        if result["success"]:
            # Save user message (image metadata)
            content = "Payment SS URL : " + image_url
            message_repo.save_message(
                db=db,
                user_id=user_id,
                sender="user",
                content=content,
                whatsapp_message_id=None
            )
            
            # Send admin notification
            from app.api.dependencies import get_notification_service
            notification_service = get_notification_service()
            
            booking = db.query(Booking).filter_by(booking_id=booking_id).first()
            if booking:
                await notification_service.notify_admin_payment_received(
                    db=db,
                    booking=booking,
                    payment_details=result.get("payment_info", {}),
                    image_url=image_url
                )
            
            # Save user-facing confirmation message
            user_confirmation = "Payment screenshot received and sent to admin for verification. You will receive confirmation shortly."
            message_repo.save_message(
                db=db,
                user_id=user_id,
                sender="bot",
                content=user_confirmation,
                whatsapp_message_id=None
            )
            
            return ChatResponse(
                status="uploaded",
                bot_response=user_confirmation,
                media_urls={"images": [image_url]}
            )
        else:
            error_msg = result.get("error", "Failed to process image. Please try again.")
            
            # Check if it's an invalid payment screenshot
            if "not appear to be a valid payment screenshot" in error_msg:
                not_valid_SS = "Please send me payment screenshot only. Thank you"
                
                # Save bot response
                message_repo.save_message(
                    db=db,
                    user_id=user_id,
                    sender="bot",
                    content=not_valid_SS,
                    whatsapp_message_id=None
                )
                
                return ChatResponse(
                    status="invalid_image",
                    bot_response=not_valid_SS
                )
            
            return ChatResponse(
                status="error",
                error=error_msg
            )
        
    except HTTPException:
        raise
    except BookingException as e:
        print(f"❌ Booking error in image upload: {e}")
        raise HTTPException(status_code=400, detail=e.message)
    except PaymentException as e:
        print(f"❌ Payment error in image upload: {e}")
        raise HTTPException(status_code=400, detail=e.message)
    except IntegrationException as e:
        print(f"❌ Integration error in image upload: {e}")
        raise HTTPException(status_code=502, detail=f"External service error: {e.message}")
    except AppException as e:
        print(f"❌ Application error in image upload: {e}")
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        import traceback
        print(f"❌ Unexpected error processing image: {e}")
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while processing the image")


@router.post("/history", response_model=List[MessageResponse])
async def get_chat_history(
    history_request: ChatHistoryRequest,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
    message_repo: MessageRepository = Depends(get_message_repository)
):
    """
    Get chat history for a user.
    
    Args:
        history_request: User ID and limit
        db: Database session
        user_repo: User repository
        message_repo: Message repository
        
    Returns:
        List of MessageResponse objects
    """
    try:
        user_id = history_request.user_id
        limit = history_request.limit
        
        # Verify user exists
        user_id_uuid = validate_and_get_user_id(user_id, user_repo, db)
        
        # Get messages
        messages = message_repo.get_chat_history(
            db=db,
            user_id=user_id_uuid,
            limit=limit,
            oldest_first=True
        )
        
        # Format response
        response = []
        for msg in messages:
            # Extract media URLs if present in bot messages
            media_urls = None
            if msg.sender == "bot":
                media_urls = extract_media_urls(msg.content)
            
            response.append(MessageResponse(
                message_id=msg.id,
                content=msg.content,
                sender=msg.sender,
                timestamp=msg.timestamp,
                media_urls=media_urls
            ))
        
        return response
        
    except HTTPException:
        raise
    except AppException as e:
        print(f"❌ Application error fetching history: {e}")
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        print(f"❌ Unexpected error fetching history: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching chat history")


@router.get("/session-info/{user_id}")
async def get_session_info(
    user_id: str,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
    session_repo: SessionRepository = Depends(get_session_repository)
):
    """
    Get current session information for a user.
    
    Args:
        user_id: User ID
        db: Database session
        user_repo: User repository
        session_repo: Session repository
        
    Returns:
        Session information dictionary
    """
    try:
        # Validate user
        user_id_uuid = validate_and_get_user_id(user_id, user_repo, db)
        
        # Get session
        session = session_repo.get_by_user_id(db, user_id_uuid)
        
        if not session:
            return {
                "status": "no_session",
                "session_id": None
            }
        
        return {
            "status": "active",
            "session_id": session.id,
            "booking_id": session.booking_id,
            "property_type": session.property_type,
            "booking_date": session.booking_date,
            "shift_type": session.shift_type,
            "min_price": float(session.min_price) if session.min_price else None,
            "max_price": float(session.max_price) if session.max_price else None,
            "max_occupancy": session.max_occupancy
        }
        
    except HTTPException:
        raise
    except AppException as e:
        print(f"❌ Application error fetching session info: {e}")
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        print(f"❌ Unexpected error fetching session info: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching session information")


@router.delete("/clear-session/{user_id}")
async def clear_session(
    user_id: str,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
    session_service: SessionService = Depends(get_session_service),
    session_repo: SessionRepository = Depends(get_session_repository)
):
    """
    Clear/reset session for a user.
    
    Args:
        user_id: User ID
        db: Database session
        user_repo: User repository
        session_service: Session service
        session_repo: Session repository
        
    Returns:
        Success status dictionary
    """
    try:
        # Validate user
        user_id_uuid = validate_and_get_user_id(user_id, user_repo, db)
        
        # Get session
        session = session_repo.get_by_user_id(db, user_id_uuid)
        
        if session:
            # Clear session using service
            result = session_service.clear_session(db=db, session_id=session.id)
            
            if not result["success"]:
                raise HTTPException(status_code=500, detail=result.get("message", "Failed to clear session"))
        
        return {"status": "success", "message": "Session cleared"}
        
    except HTTPException:
        raise
    except AppException as e:
        print(f"❌ Application error clearing session: {e}")
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        print(f"❌ Unexpected error clearing session: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while clearing the session")


@router.get("/admin/notifications")
async def get_admin_notifications(
    db: Session = Depends(get_db),
    message_repo: MessageRepository = Depends(get_message_repository)
):
    """
    Get pending payment verification requests for admin.
    Returns messages sent to admin that contain payment verification requests.
    
    Args:
        db: Database session
        message_repo: Message repository
        
    Returns:
        Dictionary with notifications list
    """
    try:
        # Get recent messages for admin user that contain verification requests
        admin_messages = (
            db.query(message_repo.model)
            .filter(
                message_repo.model.user_id == UUID(WEB_ADMIN_USER_ID),
                message_repo.model.sender == "bot",
                message_repo.model.content.like("%PAYMENT VERIFICATION REQUEST%")
            )
            .order_by(message_repo.model.timestamp.desc())
            .limit(20)
            .all()
        )
        
        notifications = []
        for msg in admin_messages:
            notifications.append({
                "message_id": msg.id,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "is_read": False
            })
        
        return {
            "status": "success",
            "notifications": notifications,
            "count": len(notifications)
        }
        
    except AppException as e:
        print(f"❌ Application error fetching admin notifications: {e}")
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        print(f"❌ Unexpected error fetching admin notifications: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching notifications")
