"""
WhatsApp webhook endpoints for Meta Business API.

This module handles webhook verification and incoming WhatsApp messages,
delegating business logic to the service layer.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime
import uuid

from app.database import get_db
from app.api.dependencies import (
    get_session_service,
    get_user_repository,
    get_session_repository,
    get_message_repository,
    get_payment_service,
    get_notification_service,
    get_media_service,
    get_whatsapp_client,
    get_cloudinary_client
)
from app.services.session_service import SessionService
from app.services.payment_service import PaymentService
from app.services.notification_service import NotificationService
from app.services.media_service import MediaService
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.message_repository import MessageRepository
from app.integrations.whatsapp import WhatsAppClient
from app.integrations.cloudinary import CloudinaryClient
from app.agents.booking_agent import BookingToolAgent
from app.agents.admin_agent import AdminAgent
from app.core.config import settings
from app.core.constants import VERIFICATION_WHATSAPP
from app.core.exceptions import (
    AppException,
    BookingException,
    PaymentException,
    PropertyException,
    IntegrationException
)
from app.utils.formatters import formatting
from app.utils.media_utils import extract_media_urls, remove_cloudinary_links
from app.models import Session as SessionModel, Message, User

router = APIRouter()

# Lazy initialization - agents will be created when first needed
_agent = None
_admin_agent = None

def get_agent():
    """Get or create the booking agent instance."""
    global _agent
    if _agent is None:
        _agent = BookingToolAgent()
    return _agent

def get_admin_agent():
    """Get or create the admin agent instance."""
    global _admin_agent
    if _admin_agent is None:
        _admin_agent = AdminAgent()
    return _admin_agent

# Webhook verification token
VERIFY_TOKEN = "my_custom_secret_token"


@router.get("/meta-webhook")
async def verify_webhook(request: Request):
    """
    Verify webhook endpoint for Meta Business API.
    
    This endpoint is called by Meta to verify the webhook URL.
    It checks the verify token and returns the challenge if valid.
    
    Args:
        request: FastAPI request object containing query parameters
        
    Returns:
        PlainTextResponse: Challenge string if token is valid, error otherwise
    """
    params = request.query_params
    
    # Extract verification parameters
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    # Verify the token matches
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print(f"✅ Webhook verified successfully")
        return PlainTextResponse(challenge)
    
    print(f"❌ Webhook verification failed - Invalid token")
    return PlainTextResponse("Invalid token", status_code=403)


@router.post("/meta-webhook")
async def receive_message(
    request: Request,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
    session_repo: SessionRepository = Depends(get_session_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
    payment_service: PaymentService = Depends(get_payment_service),
    notification_service: NotificationService = Depends(get_notification_service),
    media_service: MediaService = Depends(get_media_service),
    whatsapp_client: WhatsAppClient = Depends(get_whatsapp_client),
    cloudinary_client: CloudinaryClient = Depends(get_cloudinary_client)
):
    """
    Handle incoming WhatsApp messages from Meta Business API.
    
    This endpoint processes text messages, images, and admin commands,
    delegating business logic to appropriate services.
    
    Args:
        request: FastAPI request object containing webhook payload
        db: Database session
        session_service: Service for session management
        message_repo: Repository for message operations
        payment_service: Service for payment processing
        notification_service: Service for notifications
        media_service: Service for media handling
        whatsapp_client: Client for WhatsApp API
        cloudinary_client: Client for Cloudinary uploads
        
    Returns:
        dict: Status response
    """
    try:
        data = await request.json()
        print("📩 Incoming webhook:", data)
        
        # Extract message data
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages")
        
        # Ignore if no messages
        if not messages:
            return {"status": "ignored"}
        
        message = messages[0]
        wa_id = message.get("from")
        user_whatsapp_msg_id = message.get("id", "")
        message_type = message.get("type")
        
        # Check for duplicate messages
        if user_whatsapp_msg_id:
            existing = message_repo.get_by_whatsapp_id(db, user_whatsapp_msg_id)
            if existing:
                print(f"🔄 Message already processed: {user_whatsapp_msg_id}")
                return {"status": "already_processed"}
        
        # Get or create user and session
        user_id = _get_or_create_user(db, wa_id, user_repo)
        session_id = _get_or_create_session(db, user_id, session_repo, source="Chatbot")
        
        print(f"📱 User ID: {user_id}, Session ID: {session_id}")
        
        # Handle image messages (payment screenshots)
        if message_type == "image":
            return await _handle_image_message(
                db=db,
                message=message,
                wa_id=wa_id,
                user_id=user_id,
                session_id=session_id,
                user_whatsapp_msg_id=user_whatsapp_msg_id,
                payment_service=payment_service,
                notification_service=notification_service,
                media_service=media_service,
                whatsapp_client=whatsapp_client,
                cloudinary_client=cloudinary_client
            )
        
        # Handle text messages
        elif message_type == "text":
            text = message.get("text", {}).get("body", "")
            
            # Check if message is from admin
            if wa_id == VERIFICATION_WHATSAPP:
                return await _handle_admin_message(
                    db=db,
                    text=text,
                    session_id=session_id,
                    notification_service=notification_service,
                    message_repo=message_repo
                )
            
            # Handle regular user message
            return await _handle_text_message(
                db=db,
                text=text,
                wa_id=wa_id,
                user_id=user_id,
                session_id=session_id,
                user_whatsapp_msg_id=user_whatsapp_msg_id,
                whatsapp_client=whatsapp_client,
                message_repo=message_repo
            )
        
        return {"status": "ok"}
        
    except BookingException as e:
        print(f"❌ Booking error in webhook: {e}")
        return {"status": "error", "message": e.message, "code": e.code}
    except PaymentException as e:
        print(f"❌ Payment error in webhook: {e}")
        return {"status": "error", "message": e.message, "code": e.code}
    except PropertyException as e:
        print(f"❌ Property error in webhook: {e}")
        return {"status": "error", "message": e.message, "code": e.code}
    except IntegrationException as e:
        print(f"❌ Integration error in webhook: {e}")
        return {"status": "error", "message": f"External service error: {e.message}", "code": e.code}
    except AppException as e:
        print(f"❌ Application error in webhook: {e}")
        return {"status": "error", "message": e.message, "code": e.code}
    except Exception as e:
        print(f"❌ Unexpected error in webhook: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        return {"status": "error", "message": "An unexpected error occurred"}


async def _handle_image_message(
    db: Session,
    message: dict,
    wa_id: str,
    user_id: str,
    session_id: str,
    user_whatsapp_msg_id: str,
    payment_service: PaymentService,
    notification_service: NotificationService,
    media_service: MediaService,
    whatsapp_client: WhatsAppClient,
    cloudinary_client: CloudinaryClient
) -> dict:
    """
    Handle incoming image messages (payment screenshots).
    
    Args:
        db: Database session
        message: WhatsApp message data
        wa_id: WhatsApp ID of sender
        user_id: User ID
        session_id: Session ID
        user_whatsapp_msg_id: WhatsApp message ID
        payment_service: Payment service instance
        notification_service: Notification service instance
        media_service: Media service instance
        whatsapp_client: WhatsApp client instance
        cloudinary_client: Cloudinary client instance
        
    Returns:
        dict: Status response
        
    Raises:
        BookingException: If booking not found
        PaymentException: If payment processing fails
        IntegrationException: If external service fails
    """
    try:
        print("📸 Received image message")
        
        # Check if user has a booking
        session = db.query(SessionModel).filter_by(id=session_id).first()
        booking_id = session.booking_id if session else None
        
        if not booking_id:
            error_message = "Please first complete your booking by selecting a farmhouse/hut. After booking confirmation, then send me your payment screenshot."
            await whatsapp_client.send_message(wa_id, error_message)
            return {"status": "no_booking_required"}
        
        # Download image from WhatsApp
        media_id = message.get("image", {}).get("id")
        if not media_id:
            raise IntegrationException("No media ID found in WhatsApp message", "MEDIA_ID_MISSING")
        
        # Get media URL from WhatsApp
        import requests
        try:
            media_url_response = requests.get(
                f"https://graph.facebook.com/v23.0/{media_id}",
                headers={"Authorization": f"Bearer {settings.META_ACCESS_TOKEN}"},
                timeout=10
            )
            media_url_response.raise_for_status()
            media_url = media_url_response.json().get("url")
        except requests.RequestException as e:
            raise IntegrationException(f"Failed to get media URL from WhatsApp: {str(e)}", "WHATSAPP_MEDIA_FETCH_FAILED")
        
        # Download the actual image binary
        try:
            image_response = requests.get(
                media_url,
                headers={"Authorization": f"Bearer {settings.META_ACCESS_TOKEN}"},
                timeout=10
            )
            image_response.raise_for_status()
        except requests.RequestException as e:
            raise IntegrationException(f"Failed to download image from WhatsApp: {str(e)}", "WHATSAPP_IMAGE_DOWNLOAD_FAILED")
        
        # Upload to Cloudinary using direct bytes upload
        import cloudinary.uploader
        import asyncio
        try:
            result = await asyncio.to_thread(
                cloudinary.uploader.upload,
                image_response.content
            )
            image_url = result.get("secure_url")
            print(f"✅ Image uploaded to Cloudinary: {image_url}")
        except Exception as e:
            raise IntegrationException(f"Failed to upload image to Cloudinary: {str(e)}", "CLOUDINARY_UPLOAD_FAILED")
        
        # Save user message (image metadata)
        content = f"Payment SS URL : {image_url}"
        message_repo = MessageRepository()
        message_repo.save_message(
            db=db,
            user_id=user_id,
            sender="user",
            content=content,
            whatsapp_message_id=user_whatsapp_msg_id
        )
        
        # Store the payment screenshot URL in the booking
        from app.repositories.booking_repository import BookingRepository
        booking_repo = BookingRepository()
        booking_repo.update_payment_screenshot_url(db, booking_id, image_url)
        
        # Process payment screenshot using agent (will be refactored in Phase 8)
        agent = get_agent()
        payment_details = agent.get_response(
            incoming_text="Image received run process_payment_screenshot",
            session_id=session_id,
            whatsapp_message_id=user_whatsapp_msg_id
        )
        
        # Send notification to admin
        cloudinary_dict = {"images": [image_url]}
        admin_response = await whatsapp_client.send_message(
            VERIFICATION_WHATSAPP,
            payment_details,
            cloudinary_dict
        )
        
        # Save bot message with admin's WhatsApp message ID
        if admin_response and hasattr(admin_response, 'json'):
            admin_whatsapp_id = admin_response.json().get("messages", [{}])[0].get("id", "")
            if admin_whatsapp_id:
                message_repo.save_message(
                    db=db,
                    user_id=user_id,
                    sender="bot",
                    content=payment_details,
                    whatsapp_message_id=admin_whatsapp_id
                )
        
        print(f"✅ Payment details sent to admin")
        return {"status": "uploaded", "cloudinary_url": image_url}
        
    except (BookingException, PaymentException, IntegrationException):
        # Re-raise custom exceptions to be handled by the main webhook handler
        raise
    except Exception as e:
        print(f"❌ Unexpected error in _handle_image_message: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise IntegrationException(f"Failed to process image message: {str(e)}", "IMAGE_PROCESSING_FAILED")


async def _handle_text_message(
    db: Session,
    text: str,
    wa_id: str,
    user_id: str,
    session_id: str,
    user_whatsapp_msg_id: str,
    whatsapp_client: WhatsAppClient,
    message_repo: MessageRepository
) -> dict:
    """
    Handle incoming text messages from users.
    
    Args:
        db: Database session
        text: Message text
        wa_id: WhatsApp ID of sender
        user_id: User ID
        session_id: Session ID
        user_whatsapp_msg_id: WhatsApp message ID
        whatsapp_client: WhatsApp client instance
        message_repo: Message repository instance
        
    Returns:
        dict: Status response
        
    Raises:
        IntegrationException: If WhatsApp message sending fails
    """
    try:
        print(f"💬 Received text message: {text}")
        
        # Get bot response using agent (will be refactored in Phase 8)
        agent = get_agent()
        agent_response = agent.get_response(
            incoming_text=text,
            session_id=session_id,
            whatsapp_message_id=user_whatsapp_msg_id
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
            display_message = cleaned_response
        else:
            final_message_content = formatted_response
            display_message = formatted_response
        
        # Send WhatsApp message
        try:
            whatsapp_response = await whatsapp_client.send_message(wa_id, display_message, urls)
            
            # Only add media note if media was actually sent successfully
            if urls and whatsapp_response.get("success"):
                display_message = cleaned_response + "\n\n*Media files sent separately.*"
        except Exception as e:
            raise IntegrationException(f"Failed to send WhatsApp message: {str(e)}", "WHATSAPP_SEND_FAILED")
        
        # Extract bot's WhatsApp message ID
        bot_whatsapp_id = None
        if whatsapp_response and hasattr(whatsapp_response, 'json'):
            response_json = whatsapp_response.json()
            bot_whatsapp_id = response_json.get("messages", [{}])[0].get("id", "")
        
        # Save bot message
        message_repo.save_message(
            db=db,
            user_id=user_id,
            sender="bot",
            content=final_message_content,
            whatsapp_message_id=bot_whatsapp_id
        )
        
        print(f"✅ Message sent to user")
        return {"status": "ok"}
        
    except IntegrationException:
        # Re-raise integration exceptions to be handled by the main webhook handler
        raise
    except Exception as e:
        print(f"❌ Unexpected error in _handle_text_message: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise AppException(f"Failed to process text message: {str(e)}", "TEXT_PROCESSING_FAILED")


async def _handle_admin_message(
    db: Session,
    text: str,
    session_id: str,
    notification_service: NotificationService,
    message_repo: MessageRepository
) -> dict:
    """
    Handle incoming messages from admin (payment confirmations/rejections).
    
    Args:
        db: Database session
        text: Message text from admin
        session_id: Session ID
        notification_service: Notification service instance
        message_repo: Message repository instance
        
    Returns:
        dict: Status response
        
    Raises:
        BookingException: If session or user not found
        IntegrationException: If WhatsApp message sending fails
    """
    try:
        print(f"🔑 Received admin message: {text}")
        
        # Get admin response using admin agent (will be refactored in Phase 8)
        admin_agent = get_admin_agent()
        admin_bot_answer = admin_agent.get_response(text, session_id)
        
        # Get customer information from session
        session = db.query(SessionModel).filter_by(id=session_id).first()
        if not session or not session.user:
            print(f"❌ Session or user not found")
            raise BookingException("Session or user not found", "SESSION_NOT_FOUND")
        
        customer_phone = session.user.phone_number
        customer_user_id = session.user.user_id
        
        # Send message to customer
        try:
            whatsapp_response = await notification_service.whatsapp_client.send_message(
                customer_phone,
                admin_bot_answer
            )
        except Exception as e:
            raise IntegrationException(f"Failed to send admin response to customer: {str(e)}", "WHATSAPP_ADMIN_SEND_FAILED")
        
        # Save bot message with WhatsApp ID
        if whatsapp_response and hasattr(whatsapp_response, 'json'):
            bot_whatsapp_id = whatsapp_response.json().get("messages", [{}])[0].get("id", "")
            if bot_whatsapp_id:
                message_repo.save_message(
                    db=db,
                    user_id=customer_user_id,
                    sender="bot",
                    content=admin_bot_answer,
                    whatsapp_message_id=bot_whatsapp_id
                )
        
        print(f"✅ Admin response sent to customer")
        return {"status": "ok"}
        
    except (BookingException, IntegrationException):
        # Re-raise custom exceptions to be handled by the main webhook handler
        raise
    except Exception as e:
        print(f"❌ Unexpected error in _handle_admin_message: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise AppException(f"Failed to process admin message: {str(e)}", "ADMIN_MESSAGE_PROCESSING_FAILED")


# ============================================================================
# Helper Functions
# ============================================================================

def _get_or_create_user(
    db: Session,
    phone_number: str,
    user_repo: UserRepository
) -> str:
    """
    Get existing user by phone number or create a new one.
    
    Args:
        db: Database session
        phone_number: User's phone number (WhatsApp ID)
        user_repo: User repository instance
        
    Returns:
        str: User ID (UUID as string)
    """
    # Try to get existing user
    user = user_repo.get_by_phone(db, phone_number)
    if user:
        return str(user.user_id)
    
    # Create new user
    user_id = uuid.uuid4()
    new_user = user_repo.create(
        db=db,
        obj_in={
            "user_id": user_id,
            "phone_number": phone_number
        }
    )
    
    return str(new_user.user_id)


def _get_or_create_session(
    db: Session,
    user_id: str,
    session_repo: SessionRepository,
    source: str = "Chatbot"
) -> str:
    """
    Get existing session for user or create a new one.
    
    Args:
        db: Database session
        user_id: User ID (UUID as string)
        session_repo: Session repository instance
        source: Session source ("Chatbot" or "Website")
        
    Returns:
        str: Session ID
    """
    # Try to get existing session
    session = session_repo.get_by_user_id(db, user_id)
    if session:
        return session.id
    
    # Create new session
    session_id = str(uuid.uuid4())
    new_session = session_repo.create_or_get(
        db=db,
        user_id=user_id,
        session_id=session_id,
        source=source
    )
    
    return new_session.id
