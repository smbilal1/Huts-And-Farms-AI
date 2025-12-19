# Design Document

## Overview

This document describes the architectural design for refactoring the booking system into a modular, layered architecture. The design follows clean architecture principles with clear separation between API, business logic, data access, and external integrations.

### Architecture Principles

1. **Separation of Concerns**: Each layer has a single, well-defined responsibility
2. **Dependency Inversion**: High-level modules don't depend on low-level modules; both depend on abstractions
3. **Single Responsibility**: Each class/module has one reason to change
4. **DRY (Don't Repeat Yourself)**: Common logic is extracted and reused
5. **Testability**: Each layer can be tested independently with mocked dependencies

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Web Chat    │  │   Webhooks   │  │    Admin     │      │
│  │  Endpoints   │  │   Endpoints  │  │  Endpoints   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Booking  │ │ Payment  │ │ Property │ │  Notif   │      │
│  │ Service  │ │ Service  │ │ Service  │ │ Service  │      │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │
└───────┼────────────┼────────────┼────────────┼─────────────┘
        │            │            │            │
        ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Repository Layer                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Booking  │ │   User   │ │ Property │ │ Message  │      │
│  │   Repo   │ │   Repo   │ │   Repo   │ │   Repo   │      │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │
└───────┼────────────┼────────────┼────────────┼─────────────┘
        │            │            │            │
        ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Database (PostgreSQL)                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Integration Layer                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │ WhatsApp │ │Cloudinary│ │  Gemini  │                    │
│  │  Client  │ │  Client  │ │  Client  │                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture

### Layer Responsibilities


#### 1. API Layer (`app/api/v1/`)
- **Responsibility**: Handle HTTP requests/responses, request validation, error handling
- **Dependencies**: Services, Pydantic schemas
- **Does NOT**: Contain business logic, database operations, or external API calls

#### 2. Service Layer (`app/services/`)
- **Responsibility**: Implement business logic, orchestrate operations, manage transactions
- **Dependencies**: Repositories, Integration clients, other services
- **Does NOT**: Handle HTTP concerns or direct database operations

#### 3. Repository Layer (`app/repositories/`)
- **Responsibility**: Database operations (CRUD), query building
- **Dependencies**: Database models, SQLAlchemy session
- **Does NOT**: Contain business logic or validation

#### 4. Integration Layer (`app/integrations/`)
- **Responsibility**: External API communication, third-party service integration
- **Dependencies**: Configuration, HTTP clients
- **Does NOT**: Contain business logic

#### 5. Core Layer (`app/core/`)
- **Responsibility**: Configuration, constants, shared utilities
- **Dependencies**: Environment variables
- **Does NOT**: Depend on other application layers

---

## Components and Interfaces

### 1. Core Configuration (`app/core/config.py`)

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    SQLALCHEMY_DATABASE_URL: str
    
    # WhatsApp
    META_ACCESS_TOKEN: str
    META_PHONE_NUMBER_ID: str
    VERIFICATION_WHATSAPP: str
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    
    # Google AI
    GOOGLE_API_KEY: str
    
    # Application
    EASYPAISA_NUMBER: str = "03155699929"
    WEB_ADMIN_USER_ID: str = "216d5ab6-e8ef-4a5c-8b7c-45be19b28334"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 2. Repository Pattern

**Base Repository Interface:**
```python
from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    def get_by_id(self, db: Session, id: any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, db: Session, obj_in: dict) -> ModelType:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(self, db: Session, db_obj: ModelType, obj_in: dict) -> ModelType:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, id: any) -> None:
        obj = self.get_by_id(db, id)
        db.delete(obj)
        db.commit()
```

**Booking Repository Example:**
```python
from app.repositories.base import BaseRepository
from app.models.booking import Booking
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

class BookingRepository(BaseRepository[Booking]):
    def __init__(self):
        super().__init__(Booking)
    
    def get_by_booking_id(self, db: Session, booking_id: str) -> Optional[Booking]:
        return db.query(Booking).filter(Booking.booking_id == booking_id).first()
    
    def get_user_bookings(self, db: Session, user_id: str) -> List[Booking]:
        return db.query(Booking).filter(Booking.user_id == user_id).all()
    
    def check_availability(
        self, 
        db: Session, 
        property_id: str, 
        booking_date: datetime, 
        shift_type: str
    ) -> bool:
        existing = db.query(Booking).filter(
            Booking.property_id == property_id,
            Booking.booking_date == booking_date,
            Booking.shift_type == shift_type,
            Booking.status.in_(["Pending", "Confirmed"])
        ).first()
        return existing is None
    
    def update_status(self, db: Session, booking_id: str, status: str) -> Booking:
        booking = self.get_by_booking_id(db, booking_id)
        booking.status = status
        booking.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(booking)
        return booking
```


### 3. Service Layer Pattern

**Booking Service Example:**
```python
from app.repositories.booking_repository import BookingRepository
from app.repositories.property_repository import PropertyRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_service import NotificationService
from app.core.config import settings
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict

class BookingService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        property_repo: PropertyRepository,
        user_repo: UserRepository,
        notification_service: NotificationService
    ):
        self.booking_repo = booking_repo
        self.property_repo = property_repo
        self.user_repo = user_repo
        self.notification_service = notification_service
    
    def create_booking(
        self,
        db: Session,
        user_id: str,
        property_id: str,
        booking_date: datetime,
        shift_type: str,
        user_name: str,
        cnic: str
    ) -> Dict:
        # Validate user
        user = self.user_repo.get_by_id(db, user_id)
        if not user:
            return {"error": "User not found"}
        
        # Update user info if needed
        if not user.name:
            user.name = user_name
        if not user.cnic:
            user.cnic = cnic
        db.commit()
        
        # Check availability
        is_available = self.booking_repo.check_availability(
            db, property_id, booking_date, shift_type
        )
        if not is_available:
            return {"error": "Property already booked for this date and shift"}
        
        # Get pricing
        pricing = self.property_repo.get_pricing(
            db, property_id, booking_date, shift_type
        )
        if not pricing:
            return {"error": "Pricing not found"}
        
        # Create booking
        booking_id = f"{user_name}-{booking_date.strftime('%Y-%m-%d')}-{shift_type}"
        booking_data = {
            "booking_id": booking_id,
            "user_id": user_id,
            "property_id": property_id,
            "booking_date": booking_date,
            "shift_type": shift_type,
            "total_cost": pricing.price,
            "booking_source": "Bot",
            "status": "Pending",
            "created_at": datetime.utcnow()
        }
        
        booking = self.booking_repo.create(db, booking_data)
        
        # Send confirmation message
        message = self._format_booking_confirmation(booking, pricing)
        
        return {"message": message, "booking_id": booking_id}
    
    def _format_booking_confirmation(self, booking, pricing) -> str:
        # Format booking confirmation message
        pass
```

**Payment Service Example:**
```python
from app.repositories.booking_repository import BookingRepository
from app.integrations.gemini import GeminiClient
from app.integrations.cloudinary import CloudinaryClient
from app.services.notification_service import NotificationService
from sqlalchemy.orm import Session
from typing import Dict

class PaymentService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        gemini_client: GeminiClient,
        cloudinary_client: CloudinaryClient,
        notification_service: NotificationService
    ):
        self.booking_repo = booking_repo
        self.gemini_client = gemini_client
        self.cloudinary_client = cloudinary_client
        self.notification_service = notification_service
    
    async def process_payment_screenshot(
        self,
        db: Session,
        booking_id: str,
        image_data: str,
        is_base64: bool = True
    ) -> Dict:
        # Get booking
        booking = self.booking_repo.get_by_booking_id(db, booking_id)
        if not booking:
            return {"error": "Booking not found"}
        
        # Upload image
        if is_base64:
            image_url = await self.cloudinary_client.upload_base64(image_data)
        else:
            image_url = image_data
        
        # Extract payment info using AI
        payment_info = await self.gemini_client.extract_payment_info(image_url)
        
        if not payment_info["is_payment_screenshot"]:
            return {"error": "Invalid payment screenshot"}
        
        # Update booking status
        self.booking_repo.update_status(db, booking_id, "Waiting")
        
        # Notify admin
        await self.notification_service.notify_admin_payment_received(
            booking=booking,
            payment_info=payment_info,
            image_url=image_url
        )
        
        # Notify customer
        await self.notification_service.notify_customer_payment_received(
            booking=booking
        )
        
        return {"success": True, "message": "Payment screenshot received"}
```


### 4. Integration Clients

**WhatsApp Client:**
```python
from app.core.config import settings
import httpx
from typing import Dict, Optional

class WhatsAppClient:
    def __init__(self):
        self.token = settings.META_ACCESS_TOKEN
        self.phone_number_id = settings.META_PHONE_NUMBER_ID
        self.base_url = f"https://graph.facebook.com/v23.0/{self.phone_number_id}"
    
    async def send_message(
        self,
        recipient: str,
        message: str,
        media_urls: Optional[Dict] = None
    ) -> Dict:
        """Send WhatsApp message"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # Send media first if provided
        if media_urls:
            await self._send_media(recipient, media_urls, headers)
        
        # Send text message
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/messages",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "message_id": data.get("messages", [{}])[0].get("id")
                }
            else:
                return {"success": False, "error": response.text}
    
    async def _send_media(self, recipient: str, media_urls: Dict, headers: Dict):
        """Send media files"""
        # Implementation for sending images/videos
        pass
```

**Cloudinary Client:**
```python
import cloudinary
import cloudinary.uploader
from app.core.config import settings
import base64

class CloudinaryClient:
    def __init__(self):
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
    
    async def upload_base64(self, image_data: str) -> str:
        """Upload base64 encoded image"""
        image_bytes = base64.b64decode(image_data)
        result = cloudinary.uploader.upload(image_bytes)
        return result["secure_url"]
    
    async def upload_url(self, image_url: str) -> str:
        """Upload image from URL"""
        result = cloudinary.uploader.upload(image_url)
        return result["secure_url"]
```

**Gemini Client:**
```python
import google.generativeai as genai
from app.core.config import settings
from typing import Dict
import requests
from PIL import Image
import io

class GeminiClient:
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    async def extract_payment_info(self, image_url: str) -> Dict:
        """Extract payment information from screenshot"""
        # Download image
        response = requests.get(image_url, timeout=10)
        image = Image.open(io.BytesIO(response.content))
        
        # Analyze with Gemini
        prompt = self._get_payment_extraction_prompt()
        response = self.model.generate_content([prompt, image])
        
        # Parse response
        return self._parse_payment_response(response.text)
    
    def _get_payment_extraction_prompt(self) -> str:
        """Get prompt for payment extraction"""
        return """Extract payment information from this screenshot..."""
    
    def _parse_payment_response(self, response_text: str) -> Dict:
        """Parse Gemini response"""
        # Implementation
        pass
```

### 5. API Layer Design

**Dependency Injection Pattern:**
```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService
from app.repositories.booking_repository import BookingRepository
from app.repositories.property_repository import PropertyRepository
from app.integrations.whatsapp import WhatsAppClient

# Repository dependencies
def get_booking_repo() -> BookingRepository:
    return BookingRepository()

def get_property_repo() -> PropertyRepository:
    return PropertyRepository()

# Integration dependencies
def get_whatsapp_client() -> WhatsAppClient:
    return WhatsAppClient()

# Service dependencies
def get_booking_service(
    booking_repo: BookingRepository = Depends(get_booking_repo),
    property_repo: PropertyRepository = Depends(get_property_repo)
) -> BookingService:
    return BookingService(booking_repo, property_repo)

def get_payment_service(
    booking_repo: BookingRepository = Depends(get_booking_repo)
) -> PaymentService:
    return PaymentService(booking_repo)
```

**API Route Example:**
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.dependencies import get_booking_service, get_db
from app.services.booking_service import BookingService
from app.schemas.booking import BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.post("/", response_model=BookingResponse)
async def create_booking(
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
    booking_service: BookingService = Depends(get_booking_service)
):
    """Create a new booking"""
    result = booking_service.create_booking(db, **booking_data.dict())
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result
```


---

## Data Models

### Model Organization

Models will be split into domain-specific files while maintaining all relationships:

**`app/models/user.py`:**
- User
- Session

**`app/models/property.py`:**
- Property
- PropertyPricing
- PropertyShiftPricing
- PropertyImage
- PropertyVideo
- PropertyAmenity
- Owner
- OwnerProperty

**`app/models/booking.py`:**
- Booking

**`app/models/message.py`:**
- Message
- ImageSent
- VideoSent

**`app/models/__init__.py`:**
```python
# Import all models for SQLAlchemy registration
from app.models.user import User, Session
from app.models.property import (
    Property, PropertyPricing, PropertyShiftPricing,
    PropertyImage, PropertyVideo, PropertyAmenity,
    Owner, OwnerProperty
)
from app.models.booking import Booking
from app.models.message import Message, ImageSent, VideoSent

__all__ = [
    "User", "Session", "Property", "PropertyPricing",
    "PropertyShiftPricing", "PropertyImage", "PropertyVideo",
    "PropertyAmenity", "Owner", "OwnerProperty", "Booking",
    "Message", "ImageSent", "VideoSent"
]
```

---

## Error Handling

### Error Hierarchy

```python
# app/core/exceptions.py

class AppException(Exception):
    """Base exception for application"""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(self.message)

class BookingException(AppException):
    """Booking-related errors"""
    pass

class PaymentException(AppException):
    """Payment-related errors"""
    pass

class PropertyException(AppException):
    """Property-related errors"""
    pass

class IntegrationException(AppException):
    """External integration errors"""
    pass
```

### Error Handling in Services

```python
from app.core.exceptions import BookingException

class BookingService:
    def create_booking(self, db: Session, **kwargs):
        try:
            # Business logic
            pass
        except Exception as e:
            raise BookingException(
                message=f"Failed to create booking: {str(e)}",
                code="BOOKING_CREATE_FAILED"
            )
```

### Error Handling in API

```python
from fastapi import HTTPException
from app.core.exceptions import BookingException

@router.post("/bookings")
async def create_booking(...):
    try:
        result = booking_service.create_booking(...)
        return result
    except BookingException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Testing Strategy

### Unit Tests

**Repository Tests:**
```python
# tests/unit/repositories/test_booking_repository.py
import pytest
from app.repositories.booking_repository import BookingRepository
from app.models.booking import Booking

def test_get_by_booking_id(db_session):
    repo = BookingRepository()
    booking = repo.get_by_booking_id(db_session, "TEST-2024-01-01-Day")
    assert booking is not None
    assert booking.booking_id == "TEST-2024-01-01-Day"

def test_check_availability(db_session):
    repo = BookingRepository()
    is_available = repo.check_availability(
        db_session,
        property_id="test-property",
        booking_date=datetime(2024, 1, 1),
        shift_type="Day"
    )
    assert is_available is True
```

**Service Tests:**
```python
# tests/unit/services/test_booking_service.py
import pytest
from unittest.mock import Mock
from app.services.booking_service import BookingService

def test_create_booking_success():
    # Mock dependencies
    booking_repo = Mock()
    property_repo = Mock()
    user_repo = Mock()
    notification_service = Mock()
    
    # Setup mocks
    booking_repo.check_availability.return_value = True
    property_repo.get_pricing.return_value = Mock(price=5000)
    
    # Create service
    service = BookingService(
        booking_repo, property_repo, user_repo, notification_service
    )
    
    # Test
    result = service.create_booking(
        db=Mock(),
        user_id="test-user",
        property_id="test-property",
        booking_date=datetime(2024, 1, 1),
        shift_type="Day",
        user_name="Test User",
        cnic="1234567890123"
    )
    
    assert "error" not in result
    assert "booking_id" in result
```

### Integration Tests

```python
# tests/integration/test_booking_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_booking_endpoint():
    response = client.post(
        "/api/v1/bookings",
        json={
            "user_id": "test-user",
            "property_id": "test-property",
            "booking_date": "2024-01-01",
            "shift_type": "Day",
            "user_name": "Test User",
            "cnic": "1234567890123"
        }
    )
    assert response.status_code == 200
    assert "booking_id" in response.json()
```

---

## Migration Strategy

### Phase 1: Core & Configuration (Week 1)
1. Create `core/config.py` with Pydantic Settings
2. Create `core/constants.py`
3. Update all imports to use centralized config
4. Test: Ensure application starts without errors

### Phase 2: Models Separation (Week 1)
1. Split models into domain files
2. Update `models/__init__.py`
3. Test: Run migrations, ensure no schema changes
4. Test: Verify all relationships work

### Phase 3: Repository Layer (Week 2)
1. Create base repository
2. Implement specific repositories
3. Extract SQL queries from existing code
4. Test: Unit test each repository

### Phase 4: Integration Clients (Week 2)
1. Create WhatsApp client
2. Create Cloudinary client
3. Create Gemini client
4. Test: Mock external APIs in tests

### Phase 5: Service Layer (Week 3)
1. Create booking service
2. Create payment service
3. Create property service
4. Create notification service
5. Test: Unit test each service with mocked dependencies

### Phase 6: API Refactoring (Week 3-4)
1. Refactor web chat endpoints
2. Refactor webhook endpoints
3. Refactor admin endpoints
4. Test: Integration tests for all endpoints

### Phase 7: Agent Tools (Week 4)
1. Refactor agent tools to use services
2. Test: Ensure agents work identically

### Phase 8: Background Tasks (Week 4)
1. Refactor scheduler
2. Refactor cleanup tasks
3. Test: Verify scheduled jobs work

### Phase 9: Testing & Documentation (Week 5)
1. Write comprehensive tests
2. Update documentation
3. Create migration guide
4. Final integration testing

---

## Performance Considerations

### Database Connection Pooling
- Maintain existing pool configuration
- Use context managers for session lifecycle
- Implement connection retry logic in repositories

### Caching Strategy
- Cache property details (Redis optional)
- Cache pricing information
- Implement cache invalidation on updates

### Async Operations
- Use async for external API calls (WhatsApp, Cloudinary, Gemini)
- Keep database operations synchronous (SQLAlchemy)
- Use background tasks for non-critical operations

---

## Security Considerations

### API Security
- Maintain existing authentication
- Validate all inputs using Pydantic
- Sanitize user inputs in services

### Data Protection
- Keep sensitive data (tokens, keys) in environment variables
- Use Pydantic Settings for type-safe config
- Never log sensitive information

### External Integrations
- Implement retry logic with exponential backoff
- Set timeouts for all external calls
- Handle rate limiting gracefully

---

## Monitoring and Logging

### Logging Strategy
```python
import logging

logger = logging.getLogger(__name__)

class BookingService:
    def create_booking(self, ...):
        logger.info(f"Creating booking for user {user_id}")
        try:
            # Logic
            logger.info(f"Booking created: {booking_id}")
        except Exception as e:
            logger.error(f"Failed to create booking: {e}", exc_info=True)
            raise
```

### Metrics
- Track booking creation rate
- Monitor payment processing time
- Track external API response times
- Monitor database query performance
