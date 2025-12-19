"""
Test to verify that all fixtures are working correctly.
"""

import pytest
from datetime import datetime


def test_sample_user_data(sample_user_data):
    """Test that sample_user_data fixture works."""
    assert "user_id" in sample_user_data
    assert "name" in sample_user_data
    assert sample_user_data["name"] == "Test User"


def test_sample_property_data(sample_property_data):
    """Test that sample_property_data fixture works."""
    assert "property_id" in sample_property_data
    assert "name" in sample_property_data
    assert sample_property_data["name"] == "Test Farmhouse"


def test_sample_booking_data(sample_booking_data):
    """Test that sample_booking_data fixture works."""
    assert "booking_id" in sample_booking_data
    assert "user_id" in sample_booking_data
    assert "property_id" in sample_booking_data
    assert sample_booking_data["status"] == "Pending"


def test_db_session_fixture(db_session):
    """Test that db_session fixture works."""
    assert db_session is not None


def test_mock_whatsapp_client(mock_whatsapp_client):
    """Test that mock_whatsapp_client fixture works."""
    assert mock_whatsapp_client is not None
    assert hasattr(mock_whatsapp_client, "send_message")


def test_mock_cloudinary_client(mock_cloudinary_client):
    """Test that mock_cloudinary_client fixture works."""
    assert mock_cloudinary_client is not None
    assert hasattr(mock_cloudinary_client, "upload_base64")


def test_mock_gemini_client(mock_gemini_client):
    """Test that mock_gemini_client fixture works."""
    assert mock_gemini_client is not None
    assert hasattr(mock_gemini_client, "extract_payment_info")


def test_mock_repositories(
    mock_booking_repository,
    mock_property_repository,
    mock_user_repository,
    mock_session_repository,
    mock_message_repository
):
    """Test that all mock repository fixtures work."""
    assert mock_booking_repository is not None
    assert mock_property_repository is not None
    assert mock_user_repository is not None
    assert mock_session_repository is not None
    assert mock_message_repository is not None


def test_mock_services(
    mock_booking_service,
    mock_payment_service,
    mock_property_service,
    mock_notification_service,
    mock_session_service,
    mock_media_service
):
    """Test that all mock service fixtures work."""
    assert mock_booking_service is not None
    assert mock_payment_service is not None
    assert mock_property_service is not None
    assert mock_notification_service is not None
    assert mock_session_service is not None
    assert mock_media_service is not None


def test_future_date(future_date):
    """Test that future_date fixture works."""
    assert future_date > datetime.now()


def test_past_date(past_date):
    """Test that past_date fixture works."""
    assert past_date < datetime.now()
