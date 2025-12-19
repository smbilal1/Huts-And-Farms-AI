"""
Demo/Test endpoints for Swagger testing.

These endpoints provide a simplified interface for testing the booking agent
functionality through Swagger UI without needing a frontend.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Session as SessionModel, Message
from app.agents.booking_agent import BookingToolAgent
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.message_repository import MessageRepository

router = APIRouter(prefix="/demo", tags=["Demo/Test"])

# Lazy initialization
_booking_agent = None

def get_booking_agent():
    """Get or create the booking agent instance."""
    global _booking_agent
    if _booking_agent is None:
        _booking_agent = BookingToolAgent()
    return _booking_agent

# ==================== Request/Response Models ====================

class CreateUserRequest(BaseModel):
    """Request model for creating a test user."""
    name: str = Field(..., example="John Doe", description="User's full name")
    phone_number: str = Field(..., example="+1234567890", description="User's phone number")
    email: Optional[str] = Field(None, example="john@example.com", description="User's email (optional)")
    cnic: Optional[str] = Field(None, example="1234567890123", description="User's CNIC (optional)")

class CreateUserResponse(BaseModel):
    """Response model for user creation."""
    user_id: str
    name: str
    phone_number: str
    message: str

class ChatRequest(BaseModel):
    """Request model for sending a chat message."""
    user_id: str = Field(..., example="user-uuid-here", description="User ID from create user response")
    message: str = Field(..., example="I want to book a farmhouse", description="Message to send to the bot")

class ChatResponse(BaseModel):
    """Response model for chat."""
    user_id: str
    bot_response: str
    message_id: int
    timestamp: datetime

class MessageItem(BaseModel):
    """Individual message in chat history."""
    message_id: int
    sender: str
    content: str
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    """Response model for chat history."""
    user_id: str
    messages: List[MessageItem]
    total_count: int

class SessionInfoResponse(BaseModel):
    """Response model for session information."""
    user_id: str
    session_id: str
    property_type: Optional[str]
    booking_date: Optional[str]
    shift_type: Optional[str]
    min_price: Optional[float]
    max_price: Optional[float]
    max_occupancy: Optional[int]
    booking_id: Optional[str]

# ==================== Endpoints ====================

@router.post("/create-user", response_model=CreateUserResponse, summary="1. Create Test User")
async def create_test_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db)
):
    """
    Create a test user for demo purposes.
    
    **Steps to test the booking flow:**
    1. Create a user using this endpoint
    2. Copy the `user_id` from the response
    3. Use the `user_id` in the chat endpoint to interact with the bot
    4. Check chat history to see the conversation
    5. Check session info to see booking details
    
    **Example flow:**
    - "I want to book a farmhouse"
    - "Show me available farmhouses for tomorrow"
    - "I want to book Green Valley"
    - Provide name and CNIC when asked
    """
    try:
        user_repo = UserRepository()
        
        # Check if user with this phone already exists
        existing_user = user_repo.get_by_phone(db, request.phone_number)
        if existing_user:
            return CreateUserResponse(
                user_id=str(existing_user.user_id),
                name=existing_user.name or request.name,
                phone_number=existing_user.phone_number,
                message="User already exists. You can use this user_id for testing."
            )
        
        # Create new user
        user_data = {
            "user_id": uuid.uuid4(),
            "name": request.name,
            "phone_number": request.phone_number,
            "email": request.email,
            "cnic": request.cnic,
            "created_at": datetime.utcnow()
        }
        
        user = user_repo.create(db, user_data)
        
        return CreateUserResponse(
            user_id=str(user.user_id),
            name=user.name,
            phone_number=user.phone_number,
            message="✅ Test user created successfully! Use this user_id in the chat endpoint."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")


@router.post("/chat", response_model=ChatResponse, summary="2. Send Chat Message")
async def send_chat_message(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Send a message to the booking agent and get a response.
    
    **How to use:**
    1. Use the `user_id` from the create-user endpoint
    2. Send your message (e.g., "I want to book a farmhouse")
    3. The bot will respond with available options or questions
    4. Continue the conversation by sending more messages
    
    **Example messages to try:**
    - "I want to book a farmhouse"
    - "Show me available properties for tomorrow"
    - "I want to book Green Valley"
    - "My name is John Doe and CNIC is 1234567890123"
    - "Show me my bookings"
    """
    try:
        user_repo = UserRepository()
        session_repo = SessionRepository()
        message_repo = MessageRepository()
        
        # Verify user exists
        user_id_uuid = uuid.UUID(request.user_id)
        user = user_repo.get_by_id(db, user_id_uuid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please create a user first.")
        
        # Get or create session
        session = session_repo.create_or_get(db, user_id_uuid, str(user_id_uuid), source="Website")
        
        # Save user message
        user_message = message_repo.save_message(
            db=db,
            user_id=user_id_uuid,
            sender="user",
            content=request.message,
            timestamp=datetime.utcnow()
        )
        
        # Get bot response
        agent = get_booking_agent()
        bot_response_text = agent.get_response(
            incoming_text=request.message,
            session_id=session.id,
            whatsapp_message_id=None
        )
        
        # Save bot message
        bot_message = message_repo.save_message(
            db=db,
            user_id=user_id_uuid,
            sender="bot",
            content=bot_response_text,
            timestamp=datetime.utcnow()
        )
        
        return ChatResponse(
            user_id=request.user_id,
            bot_response=bot_response_text,
            message_id=bot_message.id,
            timestamp=bot_message.timestamp
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format. Must be a valid UUID.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@router.get("/chat-history/{user_id}", response_model=ChatHistoryResponse, summary="3. Get Chat History")
async def get_chat_history(
    user_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get the chat history for a user.
    
    **Parameters:**
    - `user_id`: The user ID from create-user endpoint
    - `limit`: Maximum number of messages to retrieve (default: 50)
    
    This shows the entire conversation between the user and the bot,
    including all booking interactions.
    """
    try:
        user_repo = UserRepository()
        message_repo = MessageRepository()
        
        # Verify user exists
        user_id_uuid = uuid.UUID(user_id)
        user = user_repo.get_by_id(db, user_id_uuid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get chat history
        messages = message_repo.get_chat_history(
            db=db,
            user_id=user_id_uuid,
            limit=limit,
            oldest_first=True
        )
        
        message_items = [
            MessageItem(
                message_id=msg.id,
                sender=msg.sender,
                content=msg.content,
                timestamp=msg.timestamp
            )
            for msg in messages
        ]
        
        return ChatHistoryResponse(
            user_id=user_id,
            messages=message_items,
            total_count=len(message_items)
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@router.get("/session-info/{user_id}", response_model=SessionInfoResponse, summary="4. Get Session Info")
async def get_session_info(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the current session information for a user.
    
    This shows what the bot knows about the user's current booking context:
    - Property type (hut/farm)
    - Booking date
    - Shift type (Day/Night/Full Day)
    - Price range
    - Max occupancy
    - Booking ID (if booking created)
    """
    try:
        user_repo = UserRepository()
        session_repo = SessionRepository()
        
        # Verify user exists
        user_id_uuid = uuid.UUID(user_id)
        user = user_repo.get_by_id(db, user_id_uuid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get session
        session = session_repo.get_by_user_id(db, user_id_uuid)
        
        if not session:
            return SessionInfoResponse(
                user_id=user_id,
                session_id="No session yet",
                property_type=None,
                booking_date=None,
                shift_type=None,
                min_price=None,
                max_price=None,
                max_occupancy=None,
                booking_id=None
            )
        
        return SessionInfoResponse(
            user_id=user_id,
            session_id=session.id,
            property_type=session.property_type,
            booking_date=session.booking_date.isoformat() if session.booking_date else None,
            shift_type=session.shift_type,
            min_price=float(session.min_price) if session.min_price else None,
            max_price=float(session.max_price) if session.max_price else None,
            max_occupancy=session.max_occupancy,
            booking_id=session.booking_id
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching session info: {str(e)}")


@router.delete("/clear-session/{user_id}", summary="5. Clear Session (Reset)")
async def clear_session(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Clear/reset the session for a user.
    
    This resets all booking context (property type, date, etc.) so you can
    start a new booking conversation from scratch.
    
    **Note:** This does NOT delete the chat history or the user.
    """
    try:
        user_repo = UserRepository()
        session_repo = SessionRepository()
        
        # Verify user exists
        user_id_uuid = uuid.UUID(user_id)
        user = user_repo.get_by_id(db, user_id_uuid)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get session
        session = session_repo.get_by_user_id(db, user_id_uuid)
        
        if session:
            # Clear session data
            session.property_type = None
            session.property_id = None
            session.booking_date = None
            session.shift_type = None
            session.min_price = None
            session.max_price = None
            session.max_occupancy = None
            session.booking_id = None
            db.commit()
            
            return {
                "status": "success",
                "message": "Session cleared successfully. You can start a new booking."
            }
        else:
            return {
                "status": "success",
                "message": "No session found to clear."
            }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing session: {str(e)}")


@router.get("/", summary="Demo API Info")
async def demo_info():
    """
    Get information about the Demo API endpoints.
    
    **Quick Start Guide:**
    
    1. **Create a test user** → `/demo/create-user`
    2. **Start chatting** → `/demo/chat` (use the user_id from step 1)
    3. **View conversation** → `/demo/chat-history/{user_id}`
    4. **Check booking status** → `/demo/session-info/{user_id}`
    5. **Reset to start over** → `/demo/clear-session/{user_id}`
    
    **Example Conversation Flow:**
    ```
    User: "I want to book a farmhouse"
    Bot: "Sure! When would you like to book?"
    
    User: "Tomorrow for day shift"
    Bot: "Here are available farmhouses..."
    
    User: "I want Green Valley"
    Bot: "Please provide your name and CNIC"
    
    User: "My name is John Doe, CNIC 1234567890123"
    Bot: "Booking created! Please send payment..."
    ```
    """
    return {
        "title": "Booking Agent Demo API",
        "description": "Test the booking agent functionality through Swagger",
        "version": "1.0.0",
        "endpoints": {
            "1": "POST /demo/create-user - Create a test user",
            "2": "POST /demo/chat - Send messages to the bot",
            "3": "GET /demo/chat-history/{user_id} - View conversation",
            "4": "GET /demo/session-info/{user_id} - Check booking status",
            "5": "DELETE /demo/clear-session/{user_id} - Reset session"
        },
        "quick_start": [
            "1. Create a user and copy the user_id",
            "2. Use that user_id to send chat messages",
            "3. View the conversation history",
            "4. Check session info to see booking details"
        ]
    }
