# Adding Features Guide

This guide provides step-by-step instructions for adding new features to the Booking System while maintaining the clean architecture and coding standards.

## Table of Contents

1. [Overview](#overview)
2. [Feature Development Process](#feature-development-process)
3. [Adding a New API Endpoint](#adding-a-new-api-endpoint)
4. [Adding Business Logic](#adding-business-logic)
5. [Adding Database Operations](#adding-database-operations)
6. [Adding External Integrations](#adding-external-integrations)
7. [Adding Background Tasks](#adding-background-tasks)
8. [Adding Utility Functions](#adding-utility-functions)
9. [Testing Your Feature](#testing-your-feature)
10. [Documentation](#documentation)
11. [Examples](#examples)

## Overview

### Architecture Layers

When adding a feature, you'll typically work across multiple layers:

```
API Layer (HTTP handling)
    ↓
Service Layer (Business logic)
    ↓
Repository Layer (Database operations)
    ↓
Database
```

Plus potentially:
- **Integration Layer**: For external APIs
- **Utils Layer**: For shared utilities
- **Tasks Layer**: For background jobs

### Key Principles

1. **Separation of Concerns**: Each layer has a specific responsibility
2. **Top-Down Development**: Start with API, then service, then repository
3. **Test-Driven Development**: Write tests as you go
4. **Documentation**: Update docs with your changes

## Feature Development Process

### Step 1: Plan Your Feature

Before coding, answer these questions:

1. **What does the feature do?** (User story)
2. **What API endpoints are needed?** (HTTP methods, paths)
3. **What business logic is required?** (Validation, calculations)
4. **What data needs to be stored?** (Database changes)
5. **What external services are needed?** (Third-party APIs)
6. **What background tasks are needed?** (Scheduled jobs)

### Step 2: Design the Implementation

Create a checklist:

- [ ] Database model changes (if any)
- [ ] Repository methods needed
- [ ] Service methods needed
- [ ] API endpoints needed
- [ ] Integration clients needed (if any)
- [ ] Background tasks needed (if any)
- [ ] Utility functions needed (if any)
- [ ] Tests to write
- [ ] Documentation to update

### Step 3: Implement Bottom-Up

1. Database models (if needed)
2. Repository methods
3. Service methods
4. API endpoints
5. Tests
6. Documentation

### Step 4: Test and Review

1. Run unit tests
2. Run integration tests
3. Manual testing
4. Code review
5. Update documentation

## Adding a New API Endpoint

### Example: Add a "Cancel Booking" Endpoint

#### 1. Define the API Route

Create or update a file in `app/api/v1/`:

```python
# app/api/v1/bookings.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, get_booking_service
from app.services.booking_service import BookingService
from app.core.exceptions import BookingException
from pydantic import BaseModel

router = APIRouter(prefix="/bookings", tags=["bookings"])

class CancelBookingRequest(BaseModel):
    booking_id: str
    reason: str

class CancelBookingResponse(BaseModel):
    success: bool
    message: str

@router.post("/cancel", response_model=CancelBookingResponse)
async def cancel_booking(
    request: CancelBookingRequest,
    db: Session = Depends(get_db),
    booking_service: BookingService = Depends(get_booking_service)
):
    """Cancel a booking.
    
    Args:
        request: Cancellation request with booking_id and reason
        db: Database session
        booking_service: Booking service instance
    
    Returns:
        Cancellation confirmation
    
    Raises:
        HTTPException: If booking cannot be cancelled
    """
    try:
        result = booking_service.cancel_booking(
            db=db,
            booking_id=request.booking_id,
            reason=request.reason
        )
        return CancelBookingResponse(
            success=True,
            message=result["message"]
        )
    except BookingException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

#### 2. Register the Router

In `app/main.py`:

```python
from app.api.v1 import bookings

app.include_router(bookings.router, prefix="/api/v1")
```

#### 3. Add Pydantic Models

If you need request/response models, define them:

```python
from pydantic import BaseModel, Field
from typing import Optional

class CancelBookingRequest(BaseModel):
    booking_id: str = Field(..., description="Booking identifier")
    reason: str = Field(..., min_length=10, description="Cancellation reason")
    
    class Config:
        schema_extra = {
            "example": {
                "booking_id": "John-2024-01-01-Day",
                "reason": "Change of plans"
            }
        }
```

## Adding Business Logic

### Example: Implement Booking Cancellation Logic

#### 1. Add Service Method

In `app/services/booking_service.py`:

```python
from app.core.exceptions import BookingException
from datetime import datetime, timedelta

class BookingService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        notification_service: NotificationService
    ):
        self.booking_repo = booking_repo
        self.notification_service = notification_service
    
    def cancel_booking(
        self,
        db: Session,
        booking_id: str,
        reason: str
    ) -> Dict:
        """Cancel a booking.
        
        Business rules:
        - Booking must exist
        - Booking must be in Pending or Confirmed status
        - Cannot cancel within 24 hours of booking date
        
        Args:
            db: Database session
            booking_id: Booking identifier
            reason: Cancellation reason
        
        Returns:
            Dictionary with cancellation details
        
        Raises:
            BookingException: If booking cannot be cancelled
        """
        # Get booking
        booking = self.booking_repo.get_by_booking_id(db, booking_id)
        if not booking:
            raise BookingException(
                message="Booking not found",
                code="BOOKING_NOT_FOUND"
            )
        
        # Check status
        if booking.status not in ["Pending", "Confirmed"]:
            raise BookingException(
                message=f"Cannot cancel booking with status {booking.status}",
                code="INVALID_STATUS"
            )
        
        # Check cancellation deadline
        now = datetime.utcnow()
        deadline = booking.booking_date - timedelta(hours=24)
        if now > deadline:
            raise BookingException(
                message="Cannot cancel within 24 hours of booking date",
                code="CANCELLATION_DEADLINE_PASSED"
            )
        
        # Update booking status
        booking = self.booking_repo.update_status(
            db=db,
            booking_id=booking_id,
            status="Cancelled"
        )
        
        # Add cancellation reason
        booking.cancellation_reason = reason
        booking.cancelled_at = now
        db.commit()
        
        # Send notifications
        self.notification_service.notify_booking_cancelled(
            booking=booking,
            reason=reason
        )
        
        return {
            "message": "Booking cancelled successfully",
            "booking_id": booking_id,
            "refund_amount": self._calculate_refund(booking)
        }
    
    def _calculate_refund(self, booking) -> float:
        """Calculate refund amount based on cancellation policy."""
        # Business logic for refund calculation
        if booking.status == "Pending":
            return booking.total_cost  # Full refund
        else:
            return booking.total_cost * 0.8  # 80% refund
```

#### 2. Add Dependency Injection

In `app/api/dependencies.py`:

```python
def get_booking_service(
    booking_repo: BookingRepository = Depends(get_booking_repo),
    notification_service: NotificationService = Depends(get_notification_service)
) -> BookingService:
    return BookingService(booking_repo, notification_service)
```

## Adding Database Operations

### Example: Add Repository Method

#### 1. Add Method to Repository

In `app/repositories/booking_repository.py`:

```python
class BookingRepository(BaseRepository[Booking]):
    def update_status(
        self,
        db: Session,
        booking_id: str,
        status: str
    ) -> Booking:
        """Update booking status.
        
        Args:
            db: Database session
            booking_id: Booking identifier
            status: New status
        
        Returns:
            Updated booking
        
        Raises:
            ValueError: If booking not found
        """
        booking = self.get_by_booking_id(db, booking_id)
        if not booking:
            raise ValueError(f"Booking {booking_id} not found")
        
        booking.status = status
        booking.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(booking)
        
        return booking
    
    def get_cancellable_bookings(
        self,
        db: Session,
        user_id: str
    ) -> List[Booking]:
        """Get bookings that can be cancelled.
        
        Args:
            db: Database session
            user_id: User identifier
        
        Returns:
            List of cancellable bookings
        """
        now = datetime.utcnow()
        deadline = now + timedelta(hours=24)
        
        return db.query(Booking).filter(
            Booking.user_id == user_id,
            Booking.status.in_(["Pending", "Confirmed"]),
            Booking.booking_date > deadline
        ).all()
```

#### 2. Add Database Model Fields (if needed)

In `app/models/booking.py`:

```python
class Booking(Base):
    __tablename__ = "bookings"
    
    # Existing fields...
    
    # New fields for cancellation
    cancellation_reason = Column(String, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    refund_amount = Column(Float, nullable=True)
```

#### 3. Create Migration (if using Alembic)

```bash
alembic revision --autogenerate -m "Add cancellation fields to booking"
alembic upgrade head
```

## Adding External Integrations

### Example: Add SMS Notification Service

#### 1. Create Integration Client

In `app/integrations/sms.py`:

```python
import httpx
from app.core.config import settings
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class SMSClient:
    """Client for SMS service integration."""
    
    def __init__(self):
        self.api_key = settings.SMS_API_KEY
        self.base_url = settings.SMS_BASE_URL
        self.timeout = 10.0
    
    async def send_sms(
        self,
        phone_number: str,
        message: str
    ) -> Dict:
        """Send SMS message.
        
        Args:
            phone_number: Recipient phone number
            message: Message content
        
        Returns:
            Dictionary with send status
        
        Raises:
            IntegrationException: If SMS sending fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/send",
                    json={
                        "to": phone_number,
                        "message": message
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    logger.info(f"SMS sent to {phone_number}")
                    return {
                        "success": True,
                        "message_id": response.json().get("id")
                    }
                else:
                    logger.error(f"SMS failed: {response.text}")
                    return {
                        "success": False,
                        "error": response.text
                    }
        
        except httpx.TimeoutException:
            logger.error(f"SMS timeout for {phone_number}")
            raise IntegrationException(
                message="SMS service timeout",
                code="SMS_TIMEOUT"
            )
        except Exception as e:
            logger.error(f"SMS error: {e}")
            raise IntegrationException(
                message=f"SMS service error: {str(e)}",
                code="SMS_ERROR"
            )
```

#### 2. Add Configuration

In `app/core/config.py`:

```python
class Settings(BaseSettings):
    # Existing settings...
    
    # SMS Service
    SMS_API_KEY: str
    SMS_BASE_URL: str = "https://api.sms-service.com"
```

#### 3. Add Dependency

In `app/api/dependencies.py`:

```python
def get_sms_client() -> SMSClient:
    return SMSClient()
```

#### 4. Use in Service

In `app/services/notification_service.py`:

```python
class NotificationService:
    def __init__(
        self,
        whatsapp_client: WhatsAppClient,
        sms_client: SMSClient
    ):
        self.whatsapp_client = whatsapp_client
        self.sms_client = sms_client
    
    async def notify_booking_cancelled(
        self,
        booking: Booking,
        reason: str
    ):
        """Send cancellation notification via SMS and WhatsApp."""
        message = f"Your booking {booking.booking_id} has been cancelled. Reason: {reason}"
        
        # Send via WhatsApp
        await self.whatsapp_client.send_message(
            recipient=booking.user.phone,
            message=message
        )
        
        # Send via SMS as backup
        await self.sms_client.send_sms(
            phone_number=booking.user.phone,
            message=message
        )
```

## Adding Background Tasks

### Example: Add Daily Report Task

#### 1. Create Task Function

In `app/tasks/report_tasks.py`:

```python
from app.repositories.booking_repository import BookingRepository
from app.integrations.email import EmailClient
from app.database import SessionLocal
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def generate_daily_report():
    """Generate and send daily booking report."""
    logger.info("Starting daily report generation")
    
    db = SessionLocal()
    try:
        booking_repo = BookingRepository()
        email_client = EmailClient()
        
        # Get yesterday's bookings
        yesterday = datetime.utcnow() - timedelta(days=1)
        bookings = booking_repo.get_bookings_by_date(db, yesterday)
        
        # Generate report
        report = _format_report(bookings)
        
        # Send email
        email_client.send_email(
            to=settings.ADMIN_EMAIL,
            subject=f"Daily Booking Report - {yesterday.strftime('%Y-%m-%d')}",
            body=report
        )
        
        logger.info(f"Daily report sent: {len(bookings)} bookings")
    
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
    
    finally:
        db.close()

def _format_report(bookings: List[Booking]) -> str:
    """Format bookings into report."""
    # Implementation
    pass
```

#### 2. Schedule the Task

In `app/tasks/scheduler.py`:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from app.tasks.report_tasks import generate_daily_report

scheduler = BackgroundScheduler()

def start_scheduler():
    """Start the task scheduler."""
    # Existing tasks...
    
    # Add daily report task (runs at 8 AM every day)
    scheduler.add_job(
        generate_daily_report,
        trigger="cron",
        hour=8,
        minute=0,
        id="daily_report"
    )
    
    scheduler.start()
```

## Adding Utility Functions

### Example: Add Date Validation Utility

In `app/utils/date_utils.py`:

```python
from datetime import datetime, timedelta
from typing import Optional

def is_valid_booking_date(
    booking_date: datetime,
    min_advance_days: int = 1,
    max_advance_days: int = 90
) -> bool:
    """Check if booking date is valid.
    
    Args:
        booking_date: Date to validate
        min_advance_days: Minimum days in advance
        max_advance_days: Maximum days in advance
    
    Returns:
        True if date is valid
    """
    now = datetime.utcnow()
    min_date = now + timedelta(days=min_advance_days)
    max_date = now + timedelta(days=max_advance_days)
    
    return min_date <= booking_date <= max_date

def get_cancellation_deadline(booking_date: datetime) -> datetime:
    """Get cancellation deadline for a booking.
    
    Args:
        booking_date: Booking date
    
    Returns:
        Deadline datetime (24 hours before booking)
    """
    return booking_date - timedelta(hours=24)

def format_booking_date(booking_date: datetime) -> str:
    """Format booking date for display.
    
    Args:
        booking_date: Date to format
    
    Returns:
        Formatted date string
    """
    return booking_date.strftime("%A, %B %d, %Y")
```

## Testing Your Feature

### 1. Write Unit Tests

Test services with mocked dependencies:

```python
# tests/unit/services/test_booking_service.py
from unittest.mock import Mock
import pytest
from app.services.booking_service import BookingService
from app.core.exceptions import BookingException

def test_cancel_booking_success():
    # Arrange
    booking_repo = Mock()
    notification_service = Mock()
    
    mock_booking = Mock()
    mock_booking.status = "Confirmed"
    mock_booking.booking_date = datetime.utcnow() + timedelta(days=2)
    
    booking_repo.get_by_booking_id.return_value = mock_booking
    booking_repo.update_status.return_value = mock_booking
    
    service = BookingService(booking_repo, notification_service)
    
    # Act
    result = service.cancel_booking(
        db=Mock(),
        booking_id="test-booking",
        reason="Change of plans"
    )
    
    # Assert
    assert result["message"] == "Booking cancelled successfully"
    booking_repo.update_status.assert_called_once()
    notification_service.notify_booking_cancelled.assert_called_once()

def test_cancel_booking_not_found():
    # Arrange
    booking_repo = Mock()
    booking_repo.get_by_booking_id.return_value = None
    
    service = BookingService(booking_repo, Mock())
    
    # Act & Assert
    with pytest.raises(BookingException) as exc:
        service.cancel_booking(Mock(), "invalid-id", "reason")
    
    assert exc.value.code == "BOOKING_NOT_FOUND"
```

### 2. Write Integration Tests

Test API endpoints end-to-end:

```python
# tests/integration/api/test_booking_api.py
from fastapi.testclient import TestClient

def test_cancel_booking_endpoint(client: TestClient, test_booking):
    # Arrange
    payload = {
        "booking_id": test_booking.booking_id,
        "reason": "Change of plans"
    }
    
    # Act
    response = client.post("/api/v1/bookings/cancel", json=payload)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data
```

### 3. Manual Testing

1. Start the application
2. Test via Swagger UI (`http://localhost:8000/docs`)
3. Test via curl or Postman
4. Verify database changes
5. Check logs

## Documentation

### 1. Update API Documentation

FastAPI auto-generates docs, but add descriptions:

```python
@router.post(
    "/cancel",
    response_model=CancelBookingResponse,
    summary="Cancel a booking",
    description="Cancel a booking with a reason. Cannot cancel within 24 hours of booking date.",
    responses={
        200: {"description": "Booking cancelled successfully"},
        400: {"description": "Invalid request or booking cannot be cancelled"},
        404: {"description": "Booking not found"}
    }
)
async def cancel_booking(...):
    pass
```

### 2. Update README

Add new features to the features list in README.md

### 3. Add Code Comments

Document complex logic:

```python
def _calculate_refund(self, booking) -> float:
    """Calculate refund amount based on cancellation policy.
    
    Refund policy:
    - Pending bookings: 100% refund
    - Confirmed bookings: 80% refund
    - Cancelled within 24h: No refund
    """
    # Implementation
```

## Examples

### Complete Example: Add Review Feature

#### 1. Database Model

```python
# app/models/review.py
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(String, primary_key=True)
    booking_id = Column(String, ForeignKey("bookings.id"))
    rating = Column(Integer)  # 1-5
    comment = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    booking = relationship("Booking", back_populates="review")
```

#### 2. Repository

```python
# app/repositories/review_repository.py
from app.repositories.base import BaseRepository
from app.models.review import Review

class ReviewRepository(BaseRepository[Review]):
    def get_by_booking_id(self, db: Session, booking_id: str):
        return db.query(Review).filter(
            Review.booking_id == booking_id
        ).first()
    
    def get_property_reviews(self, db: Session, property_id: str):
        return db.query(Review).join(Booking).filter(
            Booking.property_id == property_id
        ).all()
```

#### 3. Service

```python
# app/services/review_service.py
class ReviewService:
    def __init__(self, review_repo: ReviewRepository, booking_repo: BookingRepository):
        self.review_repo = review_repo
        self.booking_repo = booking_repo
    
    def create_review(self, db: Session, booking_id: str, rating: int, comment: str):
        # Validate booking exists and is completed
        booking = self.booking_repo.get_by_booking_id(db, booking_id)
        if not booking:
            raise ReviewException("Booking not found")
        
        if booking.status != "Completed":
            raise ReviewException("Can only review completed bookings")
        
        # Check if review already exists
        existing = self.review_repo.get_by_booking_id(db, booking_id)
        if existing:
            raise ReviewException("Review already exists")
        
        # Create review
        review_data = {
            "id": f"review-{booking_id}",
            "booking_id": booking_id,
            "rating": rating,
            "comment": comment
        }
        
        return self.review_repo.create(db, review_data)
```

#### 4. API Endpoint

```python
# app/api/v1/reviews.py
@router.post("/", response_model=ReviewResponse)
async def create_review(
    request: CreateReviewRequest,
    db: Session = Depends(get_db),
    review_service: ReviewService = Depends(get_review_service)
):
    try:
        review = review_service.create_review(
            db=db,
            booking_id=request.booking_id,
            rating=request.rating,
            comment=request.comment
        )
        return ReviewResponse.from_orm(review)
    except ReviewException as e:
        raise HTTPException(status_code=400, detail=e.message)
```

#### 5. Tests

```python
# tests/unit/services/test_review_service.py
def test_create_review_success():
    # Test implementation
    pass

# tests/integration/api/test_review_api.py
def test_create_review_endpoint():
    # Test implementation
    pass
```

## Checklist

Before submitting your feature:

- [ ] Code follows architecture patterns
- [ ] All layers implemented correctly
- [ ] Type hints added
- [ ] Docstrings added
- [ ] Error handling implemented
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Manual testing completed
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] No breaking changes (or documented)

## Questions?

Refer to:
- [Architecture Documentation](ARCHITECTURE.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- Team chat or discussions

---

**Happy coding! 🚀**
