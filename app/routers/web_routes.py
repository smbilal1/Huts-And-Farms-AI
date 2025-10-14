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
from app.agent.admin_agent import AdminAgent
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
admin_agent = AdminAgent()

WEB_ADMIN_USER_ID = uuid.UUID("216d5ab6-e8ef-4a5c-8b7c-45be19b28334")  # UUID object, not string

# Admin notification configuration
ADMIN_WEBHOOK_URL = os.getenv("ADMIN_WEBHOOK_URL", "")  # Configure your admin notification endpoint

# ==================== Request Models ====================

class WebChatMessage(BaseModel):
    message: str
    user_id: str

class WebImageMessage(BaseModel):
    image_data: str  # Base64 encoded image data OR Cloudinary URL
    user_id: str
    is_base64: bool = True  # True if image_data is base64, False if it's already a URL

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

def get_or_create_user_web(user_id: str, db) -> uuid.UUID:
    """Get user by user_id (assuming user is already authenticated)"""
    # Convert string to UUID for database query
    try:
        user_id_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    user = db.query(User).filter_by(user_id=user_id_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.user_id

def get_or_create_session(user_id: uuid.UUID, db) -> str:
    """Get or create session for user"""
    session = db.query(SessionModel).filter_by(user_id=user_id).first()
    if session:
        return session.id

    session_id = str(uuid.uuid4())
    new_session = SessionModel(id=session_id, user_id=user_id, source="Website")  # Set source as Website
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
    Send admin notification by saving to admin's chat with payment screenshot
    """
    from tools.booking import save_web_message_to_db
    
    try:
        print(f"📧 Sending admin notification:")
        print(f"   Booking ID: {booking_id}")
        print(f"   Payment Screenshot: {image_url}")
        
        # Append image URL to payment details message
        # This way the admin can see both the details AND the image
        message_with_image = f"{payment_details}\n\n📸 Payment Screenshot:\n{image_url}"
        
        # Save message to admin's conversation
        message_id = save_web_message_to_db(
            user_id=WEB_ADMIN_USER_ID,
            content=message_with_image,
            sender="bot"
        )
        
        if message_id:
            print(f"✅ Admin notification saved - Message ID: {message_id}")
            print(f"   Image URL included: {image_url}")
        else:
            print(f"❌ Failed to save admin notification")
            
    except Exception as e:
        print(f"❌ Error sending admin notification: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")

async def handle_admin_message(
    incoming_text: str,
    admin_user_id: uuid.UUID,
    db
) -> ChatResponse:
    """
    Process admin confirmation/rejection commands
    
    Args:
        incoming_text: Admin's message (e.g., "confirm ABC-123")
        admin_user_id: Admin's user ID
        db: Database session
        
    Returns:
        ChatResponse with status and admin feedback
    """
    try:
        # Get or create admin session
        session_id = get_or_create_session(admin_user_id, db)
        print(f"📋 Admin session ID: {session_id}")
        
        # Save admin's message
        admin_message = Message(
            user_id=admin_user_id,
            sender="admin",
            content=incoming_text,
            whatsapp_message_id=None,
            timestamp=datetime.utcnow()
        )
        db.add(admin_message)
        db.commit()
        print(f"✅ Admin message saved - ID: {admin_message.id}")
        
        # Call admin agent to process the command
        agent_response = admin_agent.get_response(incoming_text, session_id)
        
        print(f"🤖 Admin agent response: {agent_response}")
        
        # Check if admin_bot_answer contains customer notification data
        if isinstance(agent_response, dict):
            if agent_response.get("success") and agent_response.get("customer_phone"):
                # This is a confirmation/rejection that needs to be sent to customer
                customer_phone = agent_response.get("customer_phone")
                customer_message = agent_response.get("message", "")
                customer_user_id = agent_response.get("customer_user_id")
                
                # Determine customer type by checking their session source
                if not customer_user_id:
                    admin_feedback = "❌ Could not identify customer to send confirmation"
                    print(f"❌ No customer_user_id provided")
                else:
                    # Get customer's session to check source
                    customer_session = db.query(SessionModel).filter_by(user_id=customer_user_id).first()
                    
                    if not customer_session:
                        admin_feedback = "❌ Customer session not found"
                        print(f"❌ No session found for customer: {customer_user_id}")
                    elif customer_session.source == "Website":
                        # Website customer - save to their chat
                        from tools.booking import save_web_message_to_db
                        save_web_message_to_db(customer_user_id, customer_message, sender="bot")
                        admin_feedback = f"✅ Confirmation sent to website customer (User ID: {customer_user_id})"
                        print(f"📧 Sent confirmation to website customer: {customer_user_id}")
                    elif customer_session.source == "Chatbot":
                        # Chatbot (WhatsApp) customer - send via WhatsApp
                        if customer_phone:
                            from tools.booking import send_whatsapp_message_sync
                            result = send_whatsapp_message_sync(customer_phone, customer_message, customer_user_id, save_to_db=True)
                            if result["success"]:
                                admin_feedback = f"✅ Confirmation sent to chatbot customer via WhatsApp: {customer_phone}"
                                print(f"📱 Sent confirmation to chatbot customer: {customer_phone}")
                            else:
                                admin_feedback = f"❌ Failed to send WhatsApp message to: {customer_phone}"
                                print(f"❌ WhatsApp send failed for: {customer_phone}")
                        else:
                            admin_feedback = "❌ Chatbot customer has no phone number"
                            print(f"❌ No phone number for chatbot customer: {customer_user_id}")
                    else:
                        # Unknown source or None - fallback to old logic
                        is_web_customer = not customer_phone or customer_phone == ""
                        if is_web_customer:
                            from tools.booking import save_web_message_to_db
                            save_web_message_to_db(customer_user_id, customer_message, sender="bot")
                            admin_feedback = f"✅ Confirmation sent to customer (fallback to web)"
                            print(f"📧 Sent confirmation (fallback): {customer_user_id}")
                        else:
                            from tools.booking import send_whatsapp_message_sync
                            result = send_whatsapp_message_sync(customer_phone, customer_message, customer_user_id, save_to_db=True)
                            admin_feedback = f"✅ Confirmation sent (fallback to WhatsApp): {customer_phone}"
                            print(f"📱 Sent confirmation (fallback): {customer_phone}")
                
                # Save admin feedback to admin's chat
                admin_bot_message = Message(
                    user_id=admin_user_id,
                    sender="bot",
                    content=admin_feedback,
                    whatsapp_message_id=None,
                    timestamp=datetime.utcnow()
                )
                db.add(admin_bot_message)
                db.commit()
                
                return ChatResponse(
                    status="success",
                    bot_response=admin_feedback,
                    message_id=admin_bot_message.id
                )
            elif agent_response.get("error"):
                error_msg = agent_response.get("error")
                
                # Save error to admin's chat
                admin_bot_message = Message(
                    user_id=admin_user_id,
                    sender="bot",
                    content=error_msg,
                    whatsapp_message_id=None,
                    timestamp=datetime.utcnow()
                )
                db.add(admin_bot_message)
                db.commit()
                
                return ChatResponse(
                    status="error",
                    error=error_msg,
                    message_id=admin_bot_message.id
                )
        
        # Regular admin bot response (not a confirmation/rejection)
        admin_response_text = str(agent_response)
        
        # Save admin bot response
        admin_bot_message = Message(
            user_id=admin_user_id,
            sender="bot",
            content=admin_response_text,
            whatsapp_message_id=None,
            timestamp=datetime.utcnow()
        )
        db.add(admin_bot_message)
        db.commit()
        
        return ChatResponse(
            status="success",
            bot_response=admin_response_text,
            message_id=admin_bot_message.id
        )
        
    except Exception as e:
        print(f"❌ Error in handle_admin_message: {e}")
        print(f"   User ID: {admin_user_id}")
        print(f"   Command: {incoming_text}")
        import traceback
        print("❌ Full traceback:", traceback.format_exc())
        
        return ChatResponse(
            status="error",
            error=f"Failed to process admin command: {str(e)}"
        )

# ==================== API Routes ====================

@router.post("/web-chat/send-message", response_model=ChatResponse)
async def send_web_message(message_data: WebChatMessage):
    """
    Handle text messages from web chat
    Routes to admin agent if sender is admin, otherwise to booking agent
    """
    db = SessionLocal()
    try:
        # Get user
        user_id = get_or_create_user_web(message_data.user_id, db)
        print(f"User ID: {user_id} (type: {type(user_id)})")
        print(f"Admin ID: {WEB_ADMIN_USER_ID} (type: {type(WEB_ADMIN_USER_ID)})")
        print(f"Are they equal? {user_id == WEB_ADMIN_USER_ID}")
        
        incoming_text = message_data.message
        
        # Check if this is an admin user
        if user_id == WEB_ADMIN_USER_ID:
            print(f"🔑 Admin user detected, routing to admin agent")
            return await handle_admin_message(incoming_text, user_id, db)
        
        # Regular user flow - continue with booking agent
        # Get or create session
        session_id = get_or_create_session(user_id, db)
        print(f"Session ID: {session_id}")

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
    Accepts either base64 image data (uploads to Cloudinary) or Cloudinary URL
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

        # Upload to Cloudinary if base64, otherwise use provided URL
        if image_data.is_base64:
            try:
                # Decode base64 and upload to Cloudinary
                import base64
                image_bytes = base64.b64decode(image_data.image_data)
                result = cloudinary_upload(image_bytes)
                image_url = result["secure_url"]
                print(f"✅ Image uploaded to Cloudinary: {image_url}")
            except Exception as e:
                print(f"❌ Error uploading to Cloudinary: {e}")
                return ChatResponse(
                    status="error",
                    error="Failed to upload image. Please try again."
                )
        else:
            # Use provided Cloudinary URL
            image_url = image_data.image_data
            print(f"📎 Using provided Cloudinary URL: {image_url}")
        
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


@router.get("/web-chat/admin/notifications")
async def get_admin_notifications():
    """
    Get pending payment verification requests for admin
    Returns messages sent to admin that contain payment verification requests
    """
    db = SessionLocal()
    try:
        # Get recent messages for admin user that contain verification requests
        admin_messages = (
            db.query(Message)
            .filter(
                Message.user_id == WEB_ADMIN_USER_ID,
                Message.sender == "bot",
                Message.content.like("%PAYMENT VERIFICATION REQUEST%")
            )
            .order_by(Message.timestamp.desc())
            .limit(20)
            .all()
        )
        
        notifications = []
        for msg in admin_messages:
            notifications.append({
                "message_id": msg.id,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "is_read": False  # You can add a read status field to Message model if needed
            })
        
        return {
            "status": "success",
            "notifications": notifications,
            "count": len(notifications)
        }
        
    except Exception as e:
        print(f"❌ Error fetching admin notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()