"""
Comprehensive integration tests for all API endpoints.

This module provides end-to-end integration tests for:
- Web chat endpoints
- Webhook endpoints  
- Admin endpoints

Tests verify that responses match original behavior and all endpoints
work correctly with the refactored service layer.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4, UUID
from datetime import datetime, timedelta
import json
import os
from unittest.mock import Mock, patch, MagicMock

# Set environment variables before importing app
os.environ.setdefault("SQLALCHEMY_DATABASE_URL", "sqlite:///./test_integration.db")
os.environ.setdefault("META_ACCESS_TOKEN", "test_token")
os.environ.setdefault("META_PHONE_NUMBER_ID", "test_phone_id")
os.environ.setdefault("VERIFICATION_WHATSAPP", "1234567890")
os.environ.setdefault("CLOUDINARY_CLOUD_NAME", "test_cloud")
os.environ.setdefault("CLOUDINARY_API_KEY", "test_key")
os.environ.setdefault("CLOUDINARY_API_SECRET", "test_secret")
os.environ.setdefault("GOOGLE_API_KEY", "test_google_key")

# Mock the agent initialization before importing app
with patch('app.agent.booking_agent.ChatGoogleGenerativeAI'):
    with patch('app.agent.admin_agent.ChatGoogleGenerativeAI'):
        from app.main import app
        from app.database import Base, get_db
        from app.models import User, Session as SessionModel, Message, Booking, Property, PropertyPricing
        from app.core.constants import WEB_ADMIN_USER_ID


# ============================================================================
# Test Database Setup
# ============================================================================

# Create test database
TEST_DATABASE_URL = "sqlite:///./test_integration.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def test_db():
    """Create test database and tables for each test."""
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client with database override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def test_user(test_db):
    """Create a test user."""
    user_id = uuid4()
    user = User(
        user_id=user_id,
        name="Test User",
        phone_number="03001234567",
        email="test@example.com",
        cnic="1234567890123"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def admin_user(test_db):
    """Create admin user."""
    # WEB_ADMIN_USER_ID is already a UUID object
    admin_id = WEB_ADMIN_USER_ID if isinstance(WEB_ADMIN_USER_ID, UUID) else UUID(WEB_ADMIN_USER_ID)
    admin = User(
        user_id=admin_id,
        name="Admin User",
        phone_number="03009999999",
        email="admin@example.com"
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin


@pytest.fixture
def test_property(test_db):
    """Create a test property."""
    property_id = str(uuid4())
    prop = Property(
        property_id=property_id,
        name="Test Farmhouse",
        property_type="Farmhouse",
        location="Test Location",
        max_occupancy=10,
        description="Test property"
    )
    test_db.add(prop)
    test_db.commit()
    
    # Add pricing
    pricing = PropertyPricing(
        property_id=property_id,
        day_of_week="Monday",
        shift_type="Day",
        price=5000.0
    )
    test_db.add(pricing)
    test_db.commit()
    test_db.refresh(prop)
    return prop


@pytest.fixture
def test_session(test_db, test_user):
    """Create a test session."""
    session = SessionModel(
        id=str(uuid4()),
        user_id=test_user.user_id,
        source="Website",
        created_at=datetime.utcnow()
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    return session


@pytest.fixture
def test_booking(test_db, test_user, test_property):
    """Create a test booking."""
    booking_id = f"{test_user.name}-{datetime.now().strftime('%Y-%m-%d')}-Day"
    booking = Booking(
        booking_id=booking_id,
        user_id=test_user.user_id,
        property_id=test_property.property_id,
        booking_date=datetime.now() + timedelta(days=7),
        shift_type="Day",
        total_cost=5000.0,
        status="Pending",
        booking_source="Website"
    )
    test_db.add(booking)
    test_db.commit()
    test_db.refresh(booking)
    return booking


# ============================================================================
# Web Chat API Integration Tests
# ============================================================================

class TestWebChatIntegration:
    """Integration tests for web chat endpoints."""
    
    def test_send_message_new_user_creates_session(self, client, test_user):
        """Test that sending a message creates a session for new user."""
        response = client.post(
            "/api/web-chat/send-message",
            json={
                "message": "Hello",
                "user_id": str(test_user.user_id)
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "bot_response" in data
        assert data["bot_response"] is not None
    
    def test_send_message_invalid_user_id(self, client):
        """Test sending message with invalid user ID format."""
        response = client.post(
            "/api/web-chat/send-message",
            json={
                "message": "Hello",
                "user_id": "invalid-uuid"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid user_id format" in response.json()["detail"]
    
    def test_send_message_nonexistent_user(self, client):
        """Test sending message with non-existent user."""
        fake_uuid = str(uuid4())
        response = client.post(
            "/api/web-chat/send-message",
            json={
                "message": "Hello",
                "user_id": fake_uuid
            }
        )
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    def test_get_chat_history_empty(self, client, test_user):
        """Test getting chat history for user with no messages."""
        response = client.post(
            "/api/web-chat/history",
            json={
                "user_id": str(test_user.user_id),
                "limit": 50
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_get_chat_history_with_messages(self, client, test_user, test_db):
        """Test getting chat history with existing messages."""
        # Create some messages
        msg1 = Message(
            user_id=test_user.user_id,
            sender="user",
            content="Hello",
            timestamp=datetime.utcnow()
        )
        msg2 = Message(
            user_id=test_user.user_id,
            sender="bot",
            content="Hi there!",
            timestamp=datetime.utcnow()
        )
        test_db.add_all([msg1, msg2])
        test_db.commit()
        
        response = client.post(
            "/api/web-chat/history",
            json={
                "user_id": str(test_user.user_id),
                "limit": 50
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["sender"] == "user"
        assert data[0]["content"] == "Hello"
        assert data[1]["sender"] == "bot"
        assert data[1]["content"] == "Hi there!"
    
    def test_get_session_info_no_session(self, client, test_user):
        """Test getting session info when no session exists."""
        response = client.get(f"/api/web-chat/session-info/{test_user.user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "no_session"
        assert data["session_id"] is None
    
    def test_get_session_info_with_session(self, client, test_user, test_session):
        """Test getting session info when session exists."""
        response = client.get(f"/api/web-chat/session-info/{test_user.user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["session_id"] == test_session.id
    
    def test_clear_session_success(self, client, test_user, test_session):
        """Test clearing an existing session."""
        response = client.delete(f"/api/web-chat/clear-session/{test_user.user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "cleared" in data["message"].lower()
    
    def test_clear_session_no_session(self, client, test_user):
        """Test clearing session when none exists."""
        response = client.delete(f"/api/web-chat/clear-session/{test_user.user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


# ============================================================================
# Webhook API Integration Tests
# ============================================================================

class TestWebhookIntegration:
    """Integration tests for webhook endpoints."""
    
    def test_verify_webhook_success(self, client):
        """Test successful webhook verification."""
        response = client.get(
            "/meta-webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "my_custom_secret_token",
                "hub.challenge": "test_challenge_123"
            }
        )
        
        assert response.status_code == 200
        assert response.text == "test_challenge_123"
    
    def test_verify_webhook_invalid_token(self, client):
        """Test webhook verification with invalid token."""
        response = client.get(
            "/meta-webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "test_challenge_123"
            }
        )
        
        assert response.status_code == 403
        assert response.text == "Invalid token"
    
    def test_verify_webhook_missing_params(self, client):
        """Test webhook verification with missing parameters."""
        response = client.get(
            "/meta-webhook",
            params={
                "hub.verify_token": "my_custom_secret_token"
            }
        )
        
        assert response.status_code == 403
    
    def test_receive_message_no_messages(self, client):
        """Test webhook with no messages in payload."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": None
                    }
                }]
            }]
        }
        
        response = client.post("/meta-webhook", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
    
    def test_receive_message_duplicate(self, client, test_db):
        """Test webhook with duplicate message."""
        # Create existing message
        existing_msg = Message(
            user_id=uuid4(),
            sender="user",
            content="Test",
            whatsapp_message_id="msg_123",
            timestamp=datetime.utcnow()
        )
        test_db.add(existing_msg)
        test_db.commit()
        
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "1234567890",
                            "id": "msg_123",
                            "type": "text",
                            "text": {"body": "Hello"}
                        }]
                    }
                }]
            }]
        }
        
        response = client.post("/meta-webhook", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "already_processed"
    
    def test_receive_message_creates_user(self, client, test_db):
        """Test that receiving a message creates a new user."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "9876543210",
                            "id": "msg_new_user",
                            "type": "text",
                            "text": {"body": "Hello"}
                        }]
                    }
                }]
            }]
        }
        
        response = client.post("/meta-webhook", json=payload)
        
        assert response.status_code == 200
        
        # Verify user was created
        user = test_db.query(User).filter_by(phone_number="9876543210").first()
        assert user is not None
        assert user.phone_number == "9876543210"


# ============================================================================
# Admin API Integration Tests
# ============================================================================

class TestAdminIntegration:
    """Integration tests for admin endpoints."""
    
    def test_get_admin_notifications_empty(self, client, admin_user):
        """Test getting admin notifications when none exist."""
        response = client.get("/api/web-chat/admin/notifications")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 0
        assert len(data["notifications"]) == 0
    
    def test_get_admin_notifications_with_data(self, client, admin_user, test_db):
        """Test getting admin notifications with existing data."""
        # Create payment verification request message
        msg = Message(
            user_id=admin_user.user_id,
            sender="bot",
            content="🔔 PAYMENT VERIFICATION REQUEST\nBooking ID: Test-2024-01-15-Day",
            timestamp=datetime.utcnow()
        )
        test_db.add(msg)
        test_db.commit()
        
        response = client.get("/api/web-chat/admin/notifications")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 1
        assert len(data["notifications"]) == 1
        assert "PAYMENT VERIFICATION REQUEST" in data["notifications"][0]["content"]
    
    def test_send_admin_message_invalid_user(self, client):
        """Test sending admin message with invalid user ID."""
        response = client.post(
            "/api/web-chat/admin/send-message",
            json={
                "message": "confirm Test-2024-01-15-Day",
                "admin_user_id": "invalid-uuid"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid user_id format" in response.json()["detail"]
    
    def test_send_admin_message_non_admin_user(self, client, test_user):
        """Test sending admin message with non-admin user."""
        response = client.post(
            "/api/web-chat/admin/send-message",
            json={
                "message": "confirm Test-2024-01-15-Day",
                "admin_user_id": str(test_user.user_id)
            }
        )
        
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]
    
    def test_send_admin_message_user_not_found(self, client):
        """Test sending admin message with non-existent user."""
        fake_uuid = str(uuid4())
        response = client.post(
            "/api/web-chat/admin/send-message",
            json={
                "message": "confirm Test-2024-01-15-Day",
                "admin_user_id": fake_uuid
            }
        )
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    def test_admin_message_saves_to_database(self, client, admin_user, test_db):
        """Test that admin messages are saved to database."""
        response = client.post(
            "/api/web-chat/admin/send-message",
            json={
                "message": "test command",
                "admin_user_id": str(admin_user.user_id)
            }
        )
        
        assert response.status_code == 200
        
        # Verify message was saved
        messages = test_db.query(Message).filter_by(
            user_id=admin_user.user_id,
            sender="admin"
        ).all()
        
        assert len(messages) > 0
        assert messages[0].content == "test command"


# ============================================================================
# Cross-Endpoint Integration Tests
# ============================================================================

class TestCrossEndpointIntegration:
    """Integration tests that span multiple endpoints."""
    
    def test_complete_user_flow(self, client, test_user, test_db):
        """Test complete user flow: send message -> get history -> clear session."""
        user_id = str(test_user.user_id)
        
        # 1. Send a message
        response1 = client.post(
            "/api/web-chat/send-message",
            json={
                "message": "Hello",
                "user_id": user_id
            }
        )
        assert response1.status_code == 200
        assert response1.json()["status"] == "success"
        
        # 2. Get chat history
        response2 = client.post(
            "/api/web-chat/history",
            json={
                "user_id": user_id,
                "limit": 50
            }
        )
        assert response2.status_code == 200
        history = response2.json()
        assert len(history) > 0
        
        # 3. Get session info
        response3 = client.get(f"/api/web-chat/session-info/{user_id}")
        assert response3.status_code == 200
        assert response3.json()["status"] == "active"
        
        # 4. Clear session
        response4 = client.delete(f"/api/web-chat/clear-session/{user_id}")
        assert response4.status_code == 200
        assert response4.json()["status"] == "success"
    
    def test_webhook_creates_user_and_session(self, client, test_db):
        """Test that webhook creates both user and session."""
        phone = "1111111111"
        
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": phone,
                            "id": "msg_flow_test",
                            "type": "text",
                            "text": {"body": "Hello"}
                        }]
                    }
                }]
            }]
        }
        
        response = client.post("/meta-webhook", json=payload)
        assert response.status_code == 200
        
        # Verify user was created
        user = test_db.query(User).filter_by(phone_number=phone).first()
        assert user is not None
        
        # Verify session was created
        session = test_db.query(SessionModel).filter_by(user_id=user.user_id).first()
        assert session is not None
        assert session.source == "Chatbot"


# ============================================================================
# Response Format Validation Tests
# ============================================================================

class TestResponseFormats:
    """Tests to verify response formats match expected schemas."""
    
    def test_chat_response_format(self, client, test_user):
        """Test that chat response has correct format."""
        response = client.post(
            "/api/web-chat/send-message",
            json={
                "message": "Hello",
                "user_id": str(test_user.user_id)
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "status" in data
        assert data["status"] in ["success", "error"]
        
        if data["status"] == "success":
            assert "bot_response" in data
            assert isinstance(data["bot_response"], str)
    
    def test_history_response_format(self, client, test_user, test_db):
        """Test that history response has correct format."""
        # Create a message
        msg = Message(
            user_id=test_user.user_id,
            sender="user",
            content="Test",
            timestamp=datetime.utcnow()
        )
        test_db.add(msg)
        test_db.commit()
        
        response = client.post(
            "/api/web-chat/history",
            json={
                "user_id": str(test_user.user_id),
                "limit": 50
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            message = data[0]
            assert "message_id" in message
            assert "content" in message
            assert "sender" in message
            assert "timestamp" in message
    
    def test_session_info_response_format(self, client, test_user, test_session):
        """Test that session info response has correct format."""
        response = client.get(f"/api/web-chat/session-info/{test_user.user_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "status" in data
        assert "session_id" in data
        
        if data["status"] == "active":
            assert data["session_id"] is not None
    
    def test_admin_notifications_response_format(self, client, admin_user):
        """Test that admin notifications response has correct format."""
        response = client.get("/api/web-chat/admin/notifications")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "status" in data
        assert "notifications" in data
        assert "count" in data
        assert isinstance(data["notifications"], list)
        assert isinstance(data["count"], int)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
