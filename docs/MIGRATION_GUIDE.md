# Migration Guide: Code Modularization Refactoring

This guide helps developers migrate from the old codebase structure to the new modular architecture. It covers all import changes, new patterns, and provides practical examples for common scenarios.

---

## Table of Contents

1. [Overview](#overview)
2. [Import Changes](#import-changes)
3. [New Patterns](#new-patterns)
4. [Code Examples](#code-examples)
5. [Breaking Changes](#breaking-changes)
6. [Migration Checklist](#migration-checklist)

---

## Overview

The codebase has been refactored into a layered architecture with clear separation of concerns:

- **API Layer** (`app/api/v1/`): HTTP request/response handling
- **Service Layer** (`app/services/`): Business logic
- **Repository Layer** (`app/repositories/`): Database operations
- **Integration Layer** (`app/integrations/`): External API clients
- **Core Layer** (`app/core/`): Configuration and constants
- **Utils Layer** (`app/utils/`): Utility functions

**Key Benefits:**
- Better testability with dependency injection
- Clearer separation of concerns
- Easier to maintain and extend
- Consistent patterns across the codebase

---

## Import Changes

### Configuration and Constants

**OLD:**
```python
import os

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
EASYPAISA_NUMBER = "03155699929"  # Hardcoded
```

**NEW:**
```python
from app.core.config import settings
from app.core.constants import EASYPAISA_NUMBER, WEB_ADMIN_USER_ID

DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
META_ACCESS_TOKEN = settings.META_ACCESS_TOKEN
```

### Database Models

**OLD:**
```python
from app.chatbot.models import User, Session, Booking, Property, Message
```

**NEW:**
```python
# Import from specific domain files
from app.models.user import User, Session
from app.models.booking import Booking
from app.models.property import Property
from app.models.message import Message

# OR import from models package (backward compatible)
from app.models import User, Session, Booking, Property, Message
```

### Repositories (NEW)

```python
from app.repositories.booking_repository import BookingRepository
from app.repositories.property_repository import PropertyRepository
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.message_repository import MessageRepository
```

### Services (NEW)

```python
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService
from app.services.property_service import PropertyService
from app.services.notification_service import NotificationService
from app.services.session_service import SessionService
from app.services.media_service import MediaService
```

### Integration Clients (NEW)

```python
from app.integrations.whatsapp import WhatsAppClient
from app.integrations.cloudinary import CloudinaryClient
from app.integrations.gemini import GeminiClient
```

### Utilities

**OLD:**
```python
from app.format_message import formatting
# Scattered utility functions in various files
```

**NEW:**
```python
from app.utils.formatters import formatting, format_whatsapp_message
from app.utils.validators import validate_cnic, validate_phone, validate_booking_id
from app.utils.date_utils import parse_date, format_date, get_day_of_week
from app.utils.media_utils import extract_media_urls, remove_cloudinary_links
```

### API Dependencies

**OLD:**
```python
# Direct instantiation in routes
def some_endpoint(db: Session = Depends(get_db)):
    # Direct database queries
    booking = db.query(Booking).filter(...).first()
```

**NEW:**
```python
from app.api.dependencies import (
    get_booking_service,
    get_payment_service,
    get_property_service
)

def some_endpoint(
    db: Session = Depends(get_db),
    booking_service: BookingService = Depends(get_booking_service)
):
    # Use service methods
    booking = booking_service.get_booking(db, booking_id)
```

### Agent Tools

**OLD:**
```python
from tools.booking import create_booking, check_booking_status
from tools.bot_tools import list_properties, get_property_details
```

**NEW:**
```python
from app.agents.tools.booking_tools import create_booking, check_booking_status
from app.agents.tools.property_tools import list_properties, get_property_details
from app.agents.tools.payment_tools import process_payment_screenshot
```

### Background Tasks

**OLD:**
```python
from app.scheduler import (
    start_cleanup_scheduler,
    cleanup_inactive_sessions,
    expire_pending_bookings
)
```

**NEW:**
```python
from app.tasks.scheduler import start_cleanup_scheduler, stop_cleanup_scheduler
from app.tasks.cleanup_tasks import (
    cleanup_inactive_sessions,
    expire_pending_bookings,
    scheduled_cleanup
)
```

---

## New Patterns

### 1. Repository Pattern

Repositories handle all database operations. They accept a database session and return model instances.

**Pattern:**
```python
class SomeRepository(BaseRepository[SomeModel]):
    def __init__(self):
        super().__init__(SomeModel)
    
    def get_by_custom_field(self, db: Session, field_value: str) -> Optional[SomeModel]:
        return db.query(self.model).filter(
            self.model.custom_field == field_value
        ).first()
    
    def custom_query(self, db: Session, **filters) -> List[SomeModel]:
        query = db.query(self.model)
        # Apply filters
        return query.all()
```

**Usage:**
```python
repo = BookingRepository()
booking = repo.get_by_booking_id(db, "BOOKING-123")
user_bookings = repo.get_user_bookings(db, user_id)
```

### 2. Service Pattern

Services contain business logic and orchestrate repository calls. They handle transactions and validation.

**Pattern:**
```python
class SomeService:
    def __init__(
        self,
        some_repo: SomeRepository,
        other_repo: OtherRepository,
        integration_client: SomeClient
    ):
        self.some_repo = some_repo
        self.other_repo = other_repo
        self.integration_client = integration_client
    
    def business_operation(self, db: Session, **params) -> Dict:
        # Validate inputs
        if not self._validate_params(params):
            return {"error": "Invalid parameters"}
        
        # Perform business logic
        entity = self.some_repo.get_by_id(db, params["id"])
        if not entity:
            return {"error": "Entity not found"}
        
        # Update entity
        updated = self.some_repo.update(db, entity, params)
        
        # Call external service if needed
        await self.integration_client.notify(updated)
        
        return {"success": True, "data": updated}
    
    def _validate_params(self, params: Dict) -> bool:
        # Validation logic
        return True
```

**Usage:**
```python
service = BookingService(booking_repo, property_repo, user_repo, notification_service)
result = service.create_booking(db, user_id="123", property_id="456", ...)
```

### 3. Dependency Injection Pattern

Use FastAPI's dependency injection for services and repositories in API routes.

**Pattern:**
```python
# In app/api/dependencies.py
def get_some_repository() -> SomeRepository:
    return SomeRepository()

def get_some_service(
    some_repo: SomeRepository = Depends(get_some_repository),
    other_repo: OtherRepository = Depends(get_other_repository)
) -> SomeService:
    return SomeService(some_repo, other_repo)

# In route handler
@router.post("/endpoint")
async def endpoint(
    data: RequestModel,
    db: Session = Depends(get_db),
    service: SomeService = Depends(get_some_service)
):
    result = service.business_operation(db, **data.dict())
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
```

### 4. Integration Client Pattern

Integration clients handle external API communication with error handling and retries.

**Pattern:**
```python
class SomeIntegrationClient:
    def __init__(self):
        self.api_key = settings.SOME_API_KEY
        self.base_url = settings.SOME_BASE_URL
    
    async def call_external_api(self, **params) -> Dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/endpoint",
                    json=params,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}
```

### 5. Exception Handling Pattern

Use custom exceptions for better error handling and debugging.

**Pattern:**
```python
from app.core.exceptions import BookingException, PaymentException

# In service
def create_booking(self, db: Session, **params):
    try:
        # Business logic
        if not self._is_available(db, params):
            raise BookingException(
                message="Property not available for selected date",
                code="PROPERTY_NOT_AVAILABLE"
            )
        # Continue...
    except BookingException:
        raise  # Re-raise custom exceptions
    except Exception as e:
        raise BookingException(
            message=f"Failed to create booking: {str(e)}",
            code="BOOKING_CREATE_FAILED"
        )

# In API route
@router.post("/bookings")
async def create_booking(...):
    try:
        result = booking_service.create_booking(db, ...)
        return result
    except BookingException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Code Examples

### Example 1: Creating a Booking (Before and After)

**BEFORE:**
```python
# In route handler - mixed concerns
@router.post("/bookings")
async def create_booking(data: BookingCreate, db: Session = Depends(get_db)):
    # Direct database queries
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check availability
    existing = db.query(Booking).filter(
        Booking.property_id == data.property_id,
        Booking.booking_date == data.booking_date,
        Booking.shift_type == data.shift_type,
        Booking.status.in_(["Pending", "Confirmed"])
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already booked")
    
    # Get pricing
    pricing = db.query(PropertyShiftPricing).filter(...).first()
    
    # Create booking
    booking = Booking(
        booking_id=f"{data.user_name}-{data.booking_date}-{data.shift_type}",
        user_id=data.user_id,
        property_id=data.property_id,
        # ... more fields
    )
    db.add(booking)
    db.commit()
    
    # Send WhatsApp message
    headers = {"Authorization": f"Bearer {os.getenv('META_ACCESS_TOKEN')}"}
    # ... WhatsApp API call
    
    return {"booking_id": booking.booking_id}
```

**AFTER:**
```python
# In route handler - thin controller
@router.post("/bookings")
async def create_booking(
    data: BookingCreate,
    db: Session = Depends(get_db),
    booking_service: BookingService = Depends(get_booking_service)
):
    result = booking_service.create_booking(
        db,
        user_id=data.user_id,
        property_id=data.property_id,
        booking_date=data.booking_date,
        shift_type=data.shift_type,
        user_name=data.user_name,
        cnic=data.cnic
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result
```

### Example 2: Processing Payment Screenshot (Before and After)

**BEFORE:**
```python
# In agent tool - mixed concerns
async def process_payment_screenshot(booking_id: str, image_data: str):
    # Upload to Cloudinary
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET")
    )
    result = cloudinary.uploader.upload(base64.b64decode(image_data))
    image_url = result["secure_url"]
    
    # Call Gemini API
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash')
    # ... Gemini processing
    
    # Update booking
    db = SessionLocal()
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    booking.status = "Waiting"
    db.commit()
    
    # Send WhatsApp notification
    # ... WhatsApp API call
    
    return {"success": True}
```

**AFTER:**
```python
# In agent tool - delegates to service
async def process_payment_screenshot(booking_id: str, image_data: str):
    db = SessionLocal()
    try:
        payment_service = get_payment_service()
        result = await payment_service.process_payment_screenshot(
            db,
            booking_id=booking_id,
            image_data=image_data,
            is_base64=True
        )
        return result
    finally:
        db.close()
```

### Example 3: Searching Properties (Before and After)

**BEFORE:**
```python
# In agent tool - direct database queries
def list_properties(location: str = None, max_guests: int = None):
    db = SessionLocal()
    query = db.query(Property)
    
    if location:
        query = query.filter(Property.location.ilike(f"%{location}%"))
    if max_guests:
        query = query.filter(Property.max_guests >= max_guests)
    
    properties = query.all()
    
    # Format response
    result = []
    for prop in properties:
        result.append({
            "id": prop.id,
            "name": prop.name,
            "location": prop.location,
            # ... more fields
        })
    
    db.close()
    return result
```

**AFTER:**
```python
# In agent tool - delegates to service
def list_properties(location: str = None, max_guests: int = None):
    db = SessionLocal()
    try:
        property_service = get_property_service()
        properties = property_service.search_properties(
            db,
            location=location,
            max_guests=max_guests
        )
        return properties
    finally:
        db.close()
```

### Example 4: Adding a New Feature

**BEFORE:**
```python
# Add logic directly in route handler
@router.post("/new-feature")
async def new_feature(data: FeatureData, db: Session = Depends(get_db)):
    # Mix of database queries, business logic, and external API calls
    # Hard to test, hard to reuse
    pass
```

**AFTER:**
```python
# Step 1: Create repository method (if needed)
class FeatureRepository(BaseRepository[FeatureModel]):
    def get_by_custom_field(self, db: Session, value: str):
        return db.query(self.model).filter(...).first()

# Step 2: Create service with business logic
class FeatureService:
    def __init__(self, feature_repo: FeatureRepository):
        self.feature_repo = feature_repo
    
    def process_feature(self, db: Session, **params) -> Dict:
        # Business logic here
        entity = self.feature_repo.get_by_custom_field(db, params["value"])
        # ... more logic
        return {"success": True, "data": entity}

# Step 3: Add dependency injection
def get_feature_service(
    feature_repo: FeatureRepository = Depends(get_feature_repository)
) -> FeatureService:
    return FeatureService(feature_repo)

# Step 4: Create thin route handler
@router.post("/new-feature")
async def new_feature(
    data: FeatureData,
    db: Session = Depends(get_db),
    feature_service: FeatureService = Depends(get_feature_service)
):
    result = feature_service.process_feature(db, **data.dict())
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
```

### Example 5: Writing Tests

**BEFORE:**
```python
# Hard to test - requires full application setup
def test_create_booking():
    # Need to mock database, WhatsApp API, Cloudinary, etc.
    # All in one test
    pass
```

**AFTER:**
```python
# Test repository independently
def test_booking_repository_get_by_id(db_session):
    repo = BookingRepository()
    booking = repo.get_by_booking_id(db_session, "TEST-123")
    assert booking is not None

# Test service with mocked dependencies
def test_booking_service_create_booking():
    # Mock repositories and clients
    booking_repo = Mock()
    property_repo = Mock()
    user_repo = Mock()
    notification_service = Mock()
    
    # Setup mocks
    booking_repo.check_availability.return_value = True
    property_repo.get_pricing.return_value = Mock(price=5000)
    
    # Test service
    service = BookingService(booking_repo, property_repo, user_repo, notification_service)
    result = service.create_booking(Mock(), user_id="123", ...)
    
    assert "error" not in result
    assert "booking_id" in result

# Test API endpoint end-to-end
def test_create_booking_endpoint(client, db_session):
    response = client.post("/api/v1/bookings", json={...})
    assert response.status_code == 200
```

---

## Breaking Changes

### ⚠️ No Breaking Changes for External APIs

**Good News:** All external-facing APIs remain unchanged. The refactoring is internal only.

- All API endpoints work identically
- Request/response formats unchanged
- WhatsApp webhook behavior unchanged
- Database schema unchanged

### Internal Code Changes (For Developers)

If you have custom code that imports from the old structure, you'll need to update imports:

1. **Configuration Access**
   - Change `os.getenv()` calls to `settings.VARIABLE_NAME`
   - Import from `app.core.config` and `app.core.constants`

2. **Model Imports**
   - Models can still be imported from `app.models` (backward compatible)
   - Or import from specific domain files for better organization

3. **Direct Database Queries**
   - If you have custom scripts doing direct database queries, consider using repositories
   - Repositories provide tested, reusable query methods

4. **Agent Tools**
   - Update imports from `tools/` to `app/agents/tools/`
   - Tool functionality remains identical

5. **Background Tasks**
   - Update imports from `app.scheduler` to `app/tasks/scheduler` and `app/tasks/cleanup_tasks`
   - Scheduler behavior remains identical

### Deprecated Files

The following files have been replaced and can be removed:

- `tools/booking.py` → Moved to `app/agents/tools/booking_tools.py`
- `tools/bot_tools.py` → Split into `app/agents/tools/property_tools.py` and `app/agents/tools/payment_tools.py`
- `app/format_message.py` → Moved to `app/utils/formatters.py`

**Note:** These files may still exist for backward compatibility but should not be used in new code.

---

## Migration Checklist

Use this checklist when migrating existing code or adding new features:

### For Existing Code

- [ ] Update configuration imports to use `app.core.config.settings`
- [ ] Update constant imports to use `app.core.constants`
- [ ] Update model imports (optional, backward compatible)
- [ ] Update agent tool imports to new locations
- [ ] Update background task imports to new locations
- [ ] Remove direct `os.getenv()` calls
- [ ] Test that functionality works identically

### For New Features

- [ ] Create repository methods for database operations
- [ ] Create service class for business logic
- [ ] Create integration client if calling external APIs
- [ ] Add dependency injection functions in `app/api/dependencies.py`
- [ ] Create thin route handlers that delegate to services
- [ ] Write unit tests for repositories and services
- [ ] Write integration tests for API endpoints
- [ ] Update documentation

### For Testing

- [ ] Use test fixtures from `tests/conftest.py`
- [ ] Mock external dependencies (WhatsApp, Cloudinary, Gemini)
- [ ] Test repositories with test database
- [ ] Test services with mocked repositories
- [ ] Test API endpoints end-to-end
- [ ] Verify backward compatibility

---

## Getting Help

### Documentation

- **Architecture Overview:** See `docs/ARCHITECTURE.md`
- **Developer Guide:** See `docs/DEVELOPER_GUIDE.md`
- **Adding Features:** See `docs/ADDING_FEATURES.md`
- **Testing Guide:** See `tests/README.md`

### Common Questions

**Q: Do I need to update my API clients?**
A: No, all external APIs remain unchanged.

**Q: Will my existing database work?**
A: Yes, no schema changes were made.

**Q: How do I add a new endpoint?**
A: Follow the pattern in `docs/ADDING_FEATURES.md` - create repository, service, then route handler.

**Q: Can I still import models from `app.models`?**
A: Yes, backward compatibility is maintained.

**Q: How do I test my new feature?**
A: See `tests/README.md` for testing patterns and examples.

**Q: Where should I put utility functions?**
A: Add them to appropriate files in `app/utils/` (formatters, validators, date_utils, media_utils).

---

## Summary

The refactoring improves code organization and maintainability while preserving all functionality:

✅ **Clearer structure** - Each layer has a single responsibility
✅ **Better testability** - Components can be tested independently
✅ **Easier maintenance** - Changes are localized to specific layers
✅ **Consistent patterns** - Follow established patterns for new features
✅ **No breaking changes** - All external APIs work identically
✅ **Backward compatible** - Old imports still work where possible

Follow the patterns in this guide when working with the codebase, and refer to the other documentation for more detailed information.
