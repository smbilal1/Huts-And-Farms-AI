"""
FastAPI dependency injection functions.

This module provides dependency injection functions for repositories, services,
and integration clients used throughout the API layer. These dependencies
follow FastAPI's Depends() pattern for clean dependency management.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db

# Repository imports
from app.repositories.booking_repository import BookingRepository
from app.repositories.property_repository import PropertyRepository
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.message_repository import MessageRepository

# Service imports
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService
from app.services.property_service import PropertyService
from app.services.notification_service import NotificationService
from app.services.session_service import SessionService
from app.services.media_service import MediaService

# Integration client imports
from app.integrations.whatsapp import WhatsAppClient
from app.integrations.cloudinary import CloudinaryClient
from app.integrations.gemini import GeminiClient


# ============================================================================
# Repository Dependencies
# ============================================================================

def get_booking_repository() -> BookingRepository:
    """
    Provide BookingRepository instance.
    
    Returns:
        BookingRepository: Repository for booking operations
    """
    return BookingRepository()


def get_property_repository() -> PropertyRepository:
    """
    Provide PropertyRepository instance.
    
    Returns:
        PropertyRepository: Repository for property operations
    """
    return PropertyRepository()


def get_user_repository() -> UserRepository:
    """
    Provide UserRepository instance.
    
    Returns:
        UserRepository: Repository for user operations
    """
    return UserRepository()


def get_session_repository() -> SessionRepository:
    """
    Provide SessionRepository instance.
    
    Returns:
        SessionRepository: Repository for session operations
    """
    return SessionRepository()


def get_message_repository() -> MessageRepository:
    """
    Provide MessageRepository instance.
    
    Returns:
        MessageRepository: Repository for message operations
    """
    return MessageRepository()


# ============================================================================
# Integration Client Dependencies
# ============================================================================

def get_whatsapp_client() -> WhatsAppClient:
    """
    Provide WhatsAppClient instance.
    
    Returns:
        WhatsAppClient: Client for WhatsApp Business API operations
    """
    return WhatsAppClient()


def get_cloudinary_client() -> CloudinaryClient:
    """
    Provide CloudinaryClient instance.
    
    Returns:
        CloudinaryClient: Client for Cloudinary media upload operations
    """
    return CloudinaryClient()


def get_gemini_client() -> GeminiClient:
    """
    Provide GeminiClient instance.
    
    Returns:
        GeminiClient: Client for Gemini AI operations
    """
    return GeminiClient()


# ============================================================================
# Service Dependencies
# ============================================================================

def get_booking_service(
    booking_repo: BookingRepository = Depends(get_booking_repository),
    property_repo: PropertyRepository = Depends(get_property_repository),
    user_repo: UserRepository = Depends(get_user_repository)
) -> BookingService:
    """
    Provide BookingService instance with injected dependencies.
    
    Args:
        booking_repo: Injected BookingRepository
        property_repo: Injected PropertyRepository
        user_repo: Injected UserRepository
    
    Returns:
        BookingService: Service for booking operations
    """
    return BookingService(
        booking_repo=booking_repo,
        property_repo=property_repo,
        user_repo=user_repo
    )


def get_payment_service(
    booking_repo: BookingRepository = Depends(get_booking_repository),
    gemini_client: GeminiClient = Depends(get_gemini_client),
    cloudinary_client: CloudinaryClient = Depends(get_cloudinary_client)
) -> PaymentService:
    """
    Provide PaymentService instance with injected dependencies.
    
    Args:
        booking_repo: Injected BookingRepository
        gemini_client: Injected GeminiClient
        cloudinary_client: Injected CloudinaryClient
    
    Returns:
        PaymentService: Service for payment operations
    """
    return PaymentService(
        booking_repo=booking_repo,
        gemini_client=gemini_client,
        cloudinary_client=cloudinary_client
    )


def get_property_service(
    property_repo: PropertyRepository = Depends(get_property_repository),
    booking_repo: BookingRepository = Depends(get_booking_repository)
) -> PropertyService:
    """
    Provide PropertyService instance with injected dependencies.
    
    Args:
        property_repo: Injected PropertyRepository
        booking_repo: Injected BookingRepository
    
    Returns:
        PropertyService: Service for property operations
    """
    return PropertyService(
        property_repo=property_repo,
        booking_repo=booking_repo
    )


def get_notification_service(
    whatsapp_client: WhatsAppClient = Depends(get_whatsapp_client),
    message_repo: MessageRepository = Depends(get_message_repository),
    session_repo: SessionRepository = Depends(get_session_repository)
) -> NotificationService:
    """
    Provide NotificationService instance with injected dependencies.
    
    Args:
        whatsapp_client: Injected WhatsAppClient
        message_repo: Injected MessageRepository
        session_repo: Injected SessionRepository
    
    Returns:
        NotificationService: Service for notification operations
    """
    return NotificationService(
        whatsapp_client=whatsapp_client,
        message_repo=message_repo,
        session_repo=session_repo
    )


def get_session_service(
    session_repo: SessionRepository = Depends(get_session_repository),
    user_repo: UserRepository = Depends(get_user_repository)
) -> SessionService:
    """
    Provide SessionService instance with injected dependencies.
    
    Args:
        session_repo: Injected SessionRepository
        user_repo: Injected UserRepository
    
    Returns:
        SessionService: Service for session operations
    """
    return SessionService(
        session_repo=session_repo,
        user_repo=user_repo
    )


def get_media_service(
    cloudinary_client: CloudinaryClient = Depends(get_cloudinary_client)
) -> MediaService:
    """
    Provide MediaService instance with injected dependencies.
    
    Args:
        cloudinary_client: Injected CloudinaryClient
    
    Returns:
        MediaService: Service for media operations
    """
    return MediaService(
        cloudinary_client=cloudinary_client
    )
