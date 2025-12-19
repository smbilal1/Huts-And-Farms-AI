# API Dependencies Architecture

## Dependency Injection Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Route Handler                       │
│                                                                   │
│  @router.post("/bookings")                                       │
│  async def create_booking(                                       │
│      db: Session = Depends(get_db),                             │
│      booking_service: BookingService = Depends(get_booking_service)│
│  ):                                                              │
│      result = booking_service.create_booking(db, ...)           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ FastAPI auto-injects
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   app/api/dependencies.py                        │
│                                                                   │
│  def get_booking_service(                                        │
│      booking_repo = Depends(get_booking_repository),            │
│      property_repo = Depends(get_property_repository),          │
│      user_repo = Depends(get_user_repository)                   │
│  ) -> BookingService:                                            │
│      return BookingService(booking_repo, property_repo, user_repo)│
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ Resolves dependencies
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Repository Dependencies                       │
│                                                                   │
│  get_booking_repository() → BookingRepository()                 │
│  get_property_repository() → PropertyRepository()               │
│  get_user_repository() → UserRepository()                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ Instantiates
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BookingService                              │
│                                                                   │
│  - booking_repo: BookingRepository                               │
│  - property_repo: PropertyRepository                             │
│  - user_repo: UserRepository                                     │
│                                                                   │
│  Methods:                                                        │
│  - create_booking()                                              │
│  - confirm_booking()                                             │
│  - cancel_booking()                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Dependency Hierarchy

### Level 1: Base Dependencies (No Dependencies)
```
┌──────────────────────┐
│   Repositories       │
├──────────────────────┤
│ BookingRepository    │
│ PropertyRepository   │
│ UserRepository       │
│ SessionRepository    │
│ MessageRepository    │
└──────────────────────┘

┌──────────────────────┐
│ Integration Clients  │
├──────────────────────┤
│ WhatsAppClient       │
│ CloudinaryClient     │
│ GeminiClient         │
└──────────────────────┘
```

### Level 2: Service Dependencies (Depend on Level 1)
```
┌────────────────────────────────────────────────────────┐
│                   BookingService                        │
│  Depends on:                                            │
│  - BookingRepository                                    │
│  - PropertyRepository                                   │
│  - UserRepository                                       │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                   PaymentService                        │
│  Depends on:                                            │
│  - BookingRepository                                    │
│  - GeminiClient                                         │
│  - CloudinaryClient                                     │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                  PropertyService                        │
│  Depends on:                                            │
│  - PropertyRepository                                   │
│  - BookingRepository                                    │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                NotificationService                      │
│  Depends on:                                            │
│  - WhatsAppClient                                       │
│  - MessageRepository                                    │
│  - SessionRepository                                    │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                   SessionService                        │
│  Depends on:                                            │
│  - SessionRepository                                    │
│  - UserRepository                                       │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                    MediaService                         │
│  Depends on:                                            │
│  - CloudinaryClient                                     │
└────────────────────────────────────────────────────────┘
```

### Level 3: API Routes (Depend on Level 2)
```
┌────────────────────────────────────────────────────────┐
│                    API Endpoints                        │
│  Depend on:                                             │
│  - Services (Level 2)                                   │
│  - Database Session (get_db)                            │
└────────────────────────────────────────────────────────┘
```

## Complete Dependency Map

```
API Routes
    │
    ├─→ BookingService
    │       ├─→ BookingRepository
    │       ├─→ PropertyRepository
    │       └─→ UserRepository
    │
    ├─→ PaymentService
    │       ├─→ BookingRepository
    │       ├─→ GeminiClient
    │       └─→ CloudinaryClient
    │
    ├─→ PropertyService
    │       ├─→ PropertyRepository
    │       └─→ BookingRepository
    │
    ├─→ NotificationService
    │       ├─→ WhatsAppClient
    │       ├─→ MessageRepository
    │       └─→ SessionRepository
    │
    ├─→ SessionService
    │       ├─→ SessionRepository
    │       └─→ UserRepository
    │
    └─→ MediaService
            └─→ CloudinaryClient
```

## Usage Examples

### Example 1: Simple Repository Dependency
```python
from fastapi import APIRouter, Depends
from app.api.dependencies import get_booking_repository
from app.repositories.booking_repository import BookingRepository

router = APIRouter()

@router.get("/bookings/{booking_id}")
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    booking_repo: BookingRepository = Depends(get_booking_repository)
):
    booking = booking_repo.get_by_booking_id(db, booking_id)
    return booking
```

### Example 2: Service with Auto-Injected Dependencies
```python
from fastapi import APIRouter, Depends
from app.api.dependencies import get_booking_service
from app.services.booking_service import BookingService

router = APIRouter()

@router.post("/bookings")
def create_booking(
    booking_data: dict,
    db: Session = Depends(get_db),
    booking_service: BookingService = Depends(get_booking_service)
):
    # booking_service already has all its dependencies injected
    result = booking_service.create_booking(db, **booking_data)
    return result
```

### Example 3: Multiple Services in One Endpoint
```python
from fastapi import APIRouter, Depends
from app.api.dependencies import (
    get_booking_service,
    get_payment_service,
    get_notification_service
)

router = APIRouter()

@router.post("/bookings/{booking_id}/confirm")
async def confirm_booking_payment(
    booking_id: str,
    db: Session = Depends(get_db),
    booking_service: BookingService = Depends(get_booking_service),
    payment_service: PaymentService = Depends(get_payment_service),
    notification_service: NotificationService = Depends(get_notification_service)
):
    # Verify payment
    payment_result = payment_service.verify_payment(db, booking_id)
    
    # Confirm booking
    booking_result = booking_service.confirm_booking(db, booking_id)
    
    # Send notification
    await notification_service.notify_booking_confirmed(db, booking_result["booking"])
    
    return {"success": True}
```

## Benefits of This Architecture

1. **Testability**: Easy to mock dependencies in unit tests
2. **Maintainability**: Centralized dependency configuration
3. **Flexibility**: Easy to swap implementations
4. **Type Safety**: Full type hints for IDE support
5. **Reusability**: Dependencies shared across endpoints
6. **Separation of Concerns**: Clear boundaries between layers
7. **Automatic Resolution**: FastAPI handles dependency injection
8. **Performance**: Lightweight instantiation per request

## Testing Dependencies

```python
from unittest.mock import Mock
from app.api.dependencies import get_booking_service

# Override dependency for testing
def get_mock_booking_service():
    mock_service = Mock()
    mock_service.create_booking.return_value = {"success": True}
    return mock_service

# In test
app.dependency_overrides[get_booking_service] = get_mock_booking_service
```
