from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import uuid
import re
import cloudinary
import cloudinary.uploader
from cloudinary.uploader import upload as cloudinary_upload
import os
from dotenv import load_dotenv

from app.agent.booking_agent import BookingToolAgent
from app.database import SessionLocal
from app.chatbot.models import Session as SessionModel, Message, User
from app.format_message import formatting
from sqlalchemy import and_
from test import extract_text_from_payment_image

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

router = APIRouter()
agent = BookingToolAgent()

# Admin notification configuration
ADMIN_WEBHOOK_URL = os.getenv("ADMIN_WEBHOOK_URL", "")  # Configure your admin notification endpoint

# ==================== Request Models ====================

class WebChatMessage(BaseModel):
    message: str
    user_id: str

class WebImageMessage(BaseModel):
    image_url: str  # Frontend should upload to Cloudinary and send URL
    user_id: str

class ChatHistoryRequest(BaseModel):
    user_id: str
    limit: Optional[int] = 50

# ==================== Response Models ====================

class MessageResponse(BaseModel):
    message_id: int
    content: str
    sender: str
    timestamp: datetime
    media_urls: Optional[Dict[str, List[str]]] = None

class ChatResponse(BaseModel):
    status: str
    bot_response: Optional[str] = None
    media_urls: Optional[Dict[str, List[str]]] = None
    message_id: Optional[int] = None
    error: Optional[str] = None

# ==================== Helper Functions ====================

def get_or_create_user_web(user_id: str, db) -> str:
    """Get user by user_id (assuming user is already authenticated)"""
    user = db.query(User).filter_by(user_id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.user_id

def get_or_create_session(user_id: str, db) -> str:
    """Get or create session for user"""
    session = db.query(SessionModel).filter_by(user_id=user_id).first()
    if session:
        return session.id

    session_id = str(uuid.uuid4())
    new_session = SessionModel(id=session_id, user_id=user_id)
    db.add(new_session)
    db.commit()
    return session_id

def remove_cloudinary_links(text: str) -> str:
    """Remove Cloudinary media links from text"""
    pattern = r"https?://res\.cloudinary\.com/[^\s]+(?:\.jpg|\.jpeg|\.png|\.mp4)"
    cleaned_text = re.sub(pattern, '', text)
    cleaned_text = '\n'.join([line.strip() for line in cleaned_text.splitlines() if line.strip()])
    return cleaned_text

def extract_media_urls(text: str) -> Optional[Dict[str, List[str]]]:
    """Extract all media URLs from text"""
    pattern = r"https://[^\s]+"
    urls = re.findall(pattern, text)

    if not urls:
        return None

    media = {
        "images": [],
        "videos": []
    }

    for url in urls:
        if "/image/" in url:
            media["images"].append(url)
        elif "/video/" in url:
            media["videos"].append(url)

    return media if media["images"] or media["videos"] else None

async def notify_admin(payment_details: str, image_url: str, booking_id: str):
    """
    Send admin notification (via email, Slack, or admin dashboard)
    This keeps admin notifications separate from user chat
    """
    # TODO: Implement your admin notification system
    # Options:
    # 1. Send email to admin
    # 2. Post to Slack/Discord webhook
    # 3. Save to admin notification table
    # 4. Send to admin dashboard via WebSocket
    
    print(f"📧 Admin Notification:")
    print(f"   Booking ID: {booking_id}")
    print(f"   Payment Screenshot: {image_url}")
    print(f"   Details: {payment_details}")
    
    # Example: You could save to a separate AdminNotification table
    # Or send via email/Slack webhook
    pass

# ==================== API Routes ====================

@router.post("/web-chat/send-message", response_model=ChatResponse)
async def send_web_message(message_data: WebChatMessage):
    """
    Handle text messages from web chat
    Similar to WhatsApp webhook but for web interface
    """
    db = SessionLocal()
    try:
        # Get user
        user_id = get_or_create_user_web(message_data.user_id, db)
        print(f"User ID: {user_id}")
        
        # Get or create session
        session_id = get_or_create_session(user_id, db)
        print(f"Session ID: {session_id}")

        incoming_text = message_data.message
        
        # Save user message (no WhatsApp ID for web)
        # user_message = Message(
        #     user_id=user_id,
        #     sender="user",
        #     content=incoming_text,
        #     whatsapp_message_id=None,  # Not applicable for web
        #     timestamp=datetime.utcnow()
        # )
        # db.add(user_message)
        # db.commit()
        # db.refresh(user_message)

        # Get bot response
        agent_response = agent.get_response(
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

        # Save bot message (ONLY user-facing messages)
        bot_message = Message(
            user_id=user_id,
            sender="bot",
            content=final_message_content,
            whatsapp_message_id=None,  # Not applicable for web
            timestamp=datetime.utcnow()
        )
        db.add(bot_message)
        db.commit()
        db.refresh(bot_message)

        return ChatResponse(
            status="success",
            bot_response=final_message_content,
            media_urls=urls,
            message_id=bot_message.id
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Error in web chat: {e}")
        import traceback
        print("❌ Full traceback:", traceback.format_exc())
        return ChatResponse(
            status="error",
            error=str(e)
        )
    finally:
        db.close()


@router.post("/web-chat/send-image", response_model=ChatResponse)
async def send_web_image(image_data: WebImageMessage):
    """
    Handle image messages from web chat
    Frontend should upload image to Cloudinary first and send the URL
    """
    db = SessionLocal()
    try:
        # Get user
        user_id = get_or_create_user_web(image_data.user_id, db)
        session_id = get_or_create_session(user_id, db)
        
        session = db.query(SessionModel).filter_by(id=session_id).first()
        booking = session.booking_id

        # Check if booking exists
        if booking is None:
            error_message = "Please first complete your booking by selecting a farmhouse/hut. After booking confirmation, then send me your payment screenshot."
            
            # Save error message
            bot_message = Message(
                user_id=user_id,
                sender="bot",
                content=error_message,
                timestamp=datetime.utcnow()
            )
            db.add(bot_message)
            db.commit()
            
            return ChatResponse(
                status="no_booking_required",
                bot_response=error_message
            )

        image_url = image_data.image_url
        
        # Process payment screenshot
        result = extract_text_from_payment_image(image_url)

        if result["success"]:
            if result["is_payment_screenshot"]:
                # Save user message (image metadata)
                content = "Payment SS URL : " + image_url
                user_message = Message(
                    user_id=user_id,
                    sender="user",
                    content=content,
                    timestamp=datetime.utcnow()
                )
                db.add(user_message)
                db.commit()

                # Process payment screenshot using agent
                # This generates admin notification details but DON'T save to user's chat
                payment_details = agent.get_response(
                    incoming_text="Image received run process_payment_screenshot",
                    session_id=session_id,
                    whatsapp_message_id=None
                )

                # ✅ Send to admin via separate channel (NOT saved to user's Message table)
                await notify_admin(payment_details, image_url, str(booking))

                # ✅ Save ONLY user-facing confirmation message
                user_confirmation = "Payment screenshot received and sent to admin for verification. You will receive confirmation shortly."
                bot_message = Message(
                    user_id=user_id,
                    sender="bot",
                    content=user_confirmation,
                    timestamp=datetime.utcnow()
                )
                db.add(bot_message)
                db.commit()

                return ChatResponse(
                    status="uploaded",
                    bot_response=user_confirmation,
                    media_urls={"images": [image_url]}
                )
            else:
                not_valid_SS = "Please send me payment screenshot only. Thank you"
                
                # Save bot response
                bot_message = Message(
                    user_id=user_id,
                    sender="bot",
                    content=not_valid_SS,
                    timestamp=datetime.utcnow()
                )
                db.add(bot_message)
                db.commit()
                
                return ChatResponse(
                    status="invalid_image",
                    bot_response=not_valid_SS
                )
        else:
            error_msg = "Failed to process image. Please try again."
            return ChatResponse(
                status="error",
                error=error_msg
            )

    except Exception as e:
        print(f"❌ Error processing image: {e}")
        import traceback
        print("❌ Full traceback:", traceback.format_exc())
        return ChatResponse(
            status="error",
            error=str(e)
        )
    finally:
        db.close()


@router.post("/web-chat/history", response_model=List[MessageResponse])
async def get_chat_history(history_request: ChatHistoryRequest):
    """
    Get chat history for a user
    """
    db = SessionLocal()
    try:
        user_id = history_request.user_id
        limit = history_request.limit

        # Verify user exists
        user = db.query(User).filter_by(user_id=user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get messages
        messages = (
            db.query(Message)
            .filter(Message.user_id == user_id)
            .order_by(Message.timestamp.desc())
            .limit(limit)
            .all()
        )

        # Reverse to show oldest first
        messages = list(reversed(messages))

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

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/web-chat/session-info/{user_id}")
async def get_session_info(user_id: str):
    """
    Get current session information for a user
    """
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter_by(user_id=user_id).first()
        
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

    except Exception as e:
        print(f"❌ Error fetching session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/web-chat/clear-session/{user_id}")
async def clear_session(user_id: str):
    """
    Clear/reset session for a user (optional endpoint)
    """
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter_by(user_id=user_id).first()
        
        if session:
            # Reset session properties
            session.booking_id = None
            session.property_id = None
            session.property_type = None
            session.booking_date = None
            session.shift_type = None
            session.min_price = None
            session.max_price = None
            session.max_occupancy = None
            db.commit()

        return {"status": "success", "message": "Session cleared"}

    except Exception as e:
        print(f"❌ Error clearing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()