"""
Shared pytest fixtures and configuration.

This module provides common fixtures used across all test modules.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta

from app.database import Base
from app.models import User, Session as SessionModel, Property, PropertyPricing, Booking, Message


# Test database configuration
TEST_DATABASE_URL = "sqlite:///./test_shared.db"


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_engine):
    """Create a fresh database session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(test_db_session):
    """Alias for test_db_session for convenience."""
    return test_db_session


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_user_data():
    """Provide sample user data for tests."""
    return {
        "user_id": str(uuid4()),
        "name": "Test User",
        "phone_number": "03001234567",
        "email": "test@example.com",
        "cnic": "1234567890123"
    }


@pytest.fixture
def sample_property_data():
    """Provide sample property data for tests."""
    return {
        "property_id": str(uuid4()),
        "name": "Test Farmhouse",
        "property_type": "Farmhouse",
        "location": "Test Location",
        "max_occupancy": 10,
        "description": "A beautiful test farmhouse"
    }


@pytest.fixture
def sample_booking_data(sample_user_data, sample_property_data):
    """Provide sample booking data for tests."""
    return {
        "booking_id": f"{sample_user_data['name']}-2024-12-25-Day",
        "user_id": sample_user_data["user_id"],
        "property_id": sample_property_data["property_id"],
        "booking_date": datetime.now() + timedelta(days=7),
        "shift_type": "Day",
        "total_cost": 5000.0,
        "status": "Pending",
        "booking_source": "Website"
    }


@pytest.fixture
def sample_pricing_data(sample_property_data):
    """Provide sample pricing data for tests."""
    return {
        "property_id": sample_property_data["property_id"],
        "day_of_week": "Monday",
        "shift_type": "Day",
        "price": 5000.0
    }


@pytest.fixture
def sample_message_data(sample_user_data):
    """Provide sample message data for tests."""
    return {
        "user_id": sample_user_data["user_id"],
        "message": "Test message",
        "sender": "user",
        "timestamp": datetime.now()
    }


# ============================================================================
# Database Model Fixtures (with actual DB objects)
# ============================================================================

@pytest.fixture
def db_user(test_db_session, sample_user_data):
    """Create a user in the test database."""
    user = User(**sample_user_data)
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def db_property(test_db_session, sample_property_data):
    """Create a property in the test database."""
    property_obj = Property(**sample_property_data)
    test_db_session.add(property_obj)
    test_db_session.commit()
    test_db_session.refresh(property_obj)
    return property_obj


@pytest.fixture
def db_booking(test_db_session, db_user, db_property):
    """Create a booking in the test database."""
    booking_data = {
        "booking_id": f"{db_user.name}-2024-12-25-Day",
        "user_id": db_user.user_id,
        "property_id": db_property.property_id,
        "booking_date": datetime.now() + timedelta(days=7),
        "shift_type": "Day",
        "total_cost": 5000.0,
        "status": "Pending",
        "booking_source": "Website"
    }
    booking = Booking(**booking_data)
    test_db_session.add(booking)
    test_db_session.commit()
    test_db_session.refresh(booking)
    return booking


@pytest.fixture
def db_pricing(test_db_session, db_property):
    """Create pricing in the test database."""
    pricing_data = {
        "property_id": db_property.property_id,
        "day_of_week": "Monday",
        "shift_type": "Day",
        "price": 5000.0
    }
    pricing = PropertyPricing(**pricing_data)
    test_db_session.add(pricing)
    test_db_session.commit()
    test_db_session.refresh(pricing)
    return pricing


# ============================================================================
# Mock External Service Fixtures
# ============================================================================

@pytest.fixture
def mock_whatsapp_client():
    """Mock WhatsApp client for testing."""
    mock_client = Mock()
    mock_client.send_message = AsyncMock(return_value={
        "success": True,
        "message_id": "test_message_id_123"
    })
    mock_client.send_media = AsyncMock(return_value={
        "success": True,
        "media_id": "test_media_id_123"
    })
    return mock_client


@pytest.fixture
def mock_cloudinary_client():
    """Mock Cloudinary client for testing."""
    mock_client = Mock()
    mock_client.upload_base64 = AsyncMock(return_value="https://cloudinary.com/test_image.jpg")
    mock_client.upload_url = AsyncMock(return_value="https://cloudinary.com/test_image.jpg")
    return mock_client


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini AI client for testing."""
    mock_client = Mock()
    mock_client.extract_payment_info = AsyncMock(return_value={
        "is_payment_screenshot": True,
        "amount": 5000.0,
        "transaction_id": "TEST123456",
        "payment_method": "EasyPaisa",
        "confidence": 0.95
    })
    return mock_client


# ============================================================================
# Mock Repository Fixtures
# ============================================================================

@pytest.fixture
def mock_booking_repository():
    """Mock BookingRepository for testing services."""
    mock_repo = Mock()
    mock_repo.get_by_id = Mock(return_value=None)
    mock_repo.get_by_booking_id = Mock(return_value=None)
    mock_repo.get_user_bookings = Mock(return_value=[])
    mock_repo.check_availability = Mock(return_value=True)
    mock_repo.create = Mock()
    mock_repo.update = Mock()
    mock_repo.update_status = Mock()
    mock_repo.get_pending_bookings = Mock(return_value=[])
    mock_repo.get_expired_bookings = Mock(return_value=[])
    return mock_repo


@pytest.fixture
def mock_property_repository():
    """Mock PropertyRepository for testing services."""
    mock_repo = Mock()
    mock_repo.get_by_id = Mock(return_value=None)
    mock_repo.get_by_name = Mock(return_value=None)
    mock_repo.search_properties = Mock(return_value=[])
    mock_repo.get_pricing = Mock(return_value=None)
    mock_repo.get_images = Mock(return_value=[])
    mock_repo.get_videos = Mock(return_value=[])
    mock_repo.get_amenities = Mock(return_value=[])
    return mock_repo


@pytest.fixture
def mock_user_repository():
    """Mock UserRepository for testing services."""
    mock_repo = Mock()
    mock_repo.get_by_id = Mock(return_value=None)
    mock_repo.get_by_phone = Mock(return_value=None)
    mock_repo.get_by_email = Mock(return_value=None)
    mock_repo.get_by_cnic = Mock(return_value=None)
    mock_repo.create_or_get = Mock()
    mock_repo.create = Mock()
    mock_repo.update = Mock()
    return mock_repo


@pytest.fixture
def mock_session_repository():
    """Mock SessionRepository for testing services."""
    mock_repo = Mock()
    mock_repo.get_by_user_id = Mock(return_value=None)
    mock_repo.create_or_get = Mock()
    mock_repo.update_session_data = Mock()
    mock_repo.get_inactive_sessions = Mock(return_value=[])
    return mock_repo


@pytest.fixture
def mock_message_repository():
    """Mock MessageRepository for testing services."""
    mock_repo = Mock()
    mock_repo.get_user_messages = Mock(return_value=[])
    mock_repo.get_chat_history = Mock(return_value=[])
    mock_repo.save_message = Mock()
    mock_repo.create = Mock()
    return mock_repo


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_booking_service():
    """Mock BookingService for testing API endpoints."""
    mock_service = Mock()
    mock_service.create_booking = Mock(return_value={"booking_id": "TEST-2024-12-25-Day"})
    mock_service.confirm_booking = Mock(return_value={"success": True})
    mock_service.cancel_booking = Mock(return_value={"success": True})
    mock_service.get_user_bookings = Mock(return_value=[])
    mock_service.check_booking_status = Mock(return_value={"status": "Pending"})
    return mock_service


@pytest.fixture
def mock_payment_service():
    """Mock PaymentService for testing API endpoints."""
    mock_service = Mock()
    mock_service.process_payment_screenshot = AsyncMock(return_value={"success": True})
    mock_service.process_payment_details = Mock(return_value={"success": True})
    mock_service.verify_payment = Mock(return_value={"verified": True})
    mock_service.get_payment_instructions = Mock(return_value="Payment instructions")
    return mock_service


@pytest.fixture
def mock_property_service():
    """Mock PropertyService for testing API endpoints."""
    mock_service = Mock()
    mock_service.search_properties = Mock(return_value=[])
    mock_service.get_property_details = Mock(return_value=None)
    mock_service.get_property_images = Mock(return_value=[])
    mock_service.get_property_videos = Mock(return_value=[])
    mock_service.check_availability = Mock(return_value=True)
    return mock_service


@pytest.fixture
def mock_notification_service():
    """Mock NotificationService for testing."""
    mock_service = Mock()
    mock_service.notify_admin_payment_received = AsyncMock(return_value={"success": True})
    mock_service.notify_customer_payment_received = AsyncMock(return_value={"success": True})
    mock_service.notify_booking_confirmed = AsyncMock(return_value={"success": True})
    mock_service.notify_booking_cancelled = AsyncMock(return_value={"success": True})
    return mock_service


@pytest.fixture
def mock_session_service():
    """Mock SessionService for testing."""
    mock_service = Mock()
    mock_service.get_or_create_session = Mock(return_value=None)
    mock_service.update_session_data = Mock()
    mock_service.clear_session = Mock()
    return mock_service


@pytest.fixture
def mock_media_service():
    """Mock MediaService for testing."""
    mock_service = Mock()
    mock_service.upload_image = AsyncMock(return_value="https://cloudinary.com/test.jpg")
    mock_service.extract_media_urls = Mock(return_value={"images": [], "videos": []})
    mock_service.remove_media_links = Mock(return_value="cleaned text")
    return mock_service


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock database session for unit tests."""
    mock_session = MagicMock()
    mock_session.query = Mock()
    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.rollback = Mock()
    mock_session.refresh = Mock()
    mock_session.close = Mock()
    return mock_session


@pytest.fixture
def future_date():
    """Provide a future date for testing."""
    return datetime.now() + timedelta(days=7)


@pytest.fixture
def past_date():
    """Provide a past date for testing."""
    return datetime.now() - timedelta(days=7)
