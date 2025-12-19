# Architecture Documentation

## Overview

The Booking System follows a **layered architecture** pattern with clear separation of concerns. This document provides detailed information about the system's architecture, design patterns, and component interactions.

## Architectural Principles

### 1. Separation of Concerns
Each layer has a single, well-defined responsibility:
- **API Layer**: HTTP handling
- **Service Layer**: Business logic
- **Repository Layer**: Data access
- **Integration Layer**: External APIs

### 2. Dependency Inversion
- High-level modules (services) don't depend on low-level modules (repositories)
- Both depend on abstractions (interfaces/protocols)
- Dependencies are injected, not instantiated

### 3. Single Responsibility
- Each class has one reason to change
- Functions are focused and do one thing well
- Modules are cohesive

### 4. DRY (Don't Repeat Yourself)
- Common logic is extracted into utilities
- Base classes provide shared functionality
- Configuration is centralized

### 5. Testability
- Each layer can be tested independently
- Dependencies can be mocked
- Pure functions where possible

## System Architecture

### High-Level Architecture Diagram

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

## Layer Details

### API Layer (`app/api/`)

**Purpose**: Handle HTTP requests and responses

**Responsibilities**:
- Request validation using Pydantic models
- Response formatting
- Error handling and HTTP status codes
- Dependency injection setup
- Route organization

**Key Components**:
- `app/api/v1/web_chat.py` - Web chat endpoints
- `app/api/v1/webhooks.py` - WhatsApp webhook handlers
- `app/api/v1/admin.py` - Admin endpoints
- `app/api/dependencies.py` - Dependency injection functions

**Example**:
```python
@router.post("/bookings")
async def create_booking(
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
    booking_service: BookingService = Depends(get_booking_service)
):
    """API endpoint only handles HTTP concerns"""
    try:
        result = booking_service.create_booking(db, **booking_data.dict())
        return JSONResponse(content=result, status_code=200)
    except BookingException as e:
        raise HTTPException(status_code=400, detail=e.message)
```

**Rules**:
- ✅ DO: Validate requests, format responses, handle HTTP errors
- ❌ DON'T: Implement business logic, make database calls, call external APIs

### Service Layer (`app/services/`)

**Purpose**: Implement business logic and orchestrate operations

**Responsibilities**:
- Business rule enforcement
- Transaction management
- Orchestrating multiple repository calls
- Calling integration clients
- Data transformation and validation
- Error handling with custom exceptions

**Key Components**:
- `booking_service.py` - Booking creation, confirmation, cancellation
- `payment_service.py` - Payment processing and verification
- `property_service.py` - Property search and availability
- `notification_service.py` - Multi-channel notifications
- `session_service.py` - Session management
- `media_service.py` - Media upload and processing

**Example**:
```python
class BookingService:
    def __init__(
        self,
        booking_repo: BookingRepository,
        property_repo: PropertyRepository,
        notification_service: NotificationService
    ):
        self.booking_repo = booking_repo
        self.property_repo = property_repo
        self.notification_service = notification_service
    
    def create_booking(self, db: Session, **kwargs) -> Dict:
        """Business logic orchestration"""
        # Validate availability
        if not self.booking_repo.check_availability(db, ...):
            raise BookingException("Property not available")
        
        # Get pricing
        pricing = self.property_repo.get_pricing(db, ...)
        
        # Create booking
        booking = self.booking_repo.create(db, ...)
        
        # Send notifications
        self.notification_service.notify_booking_created(booking)
        
        return {"booking_id": booking.booking_id}
```

**Rules**:
- ✅ DO: Implement business logic, orchestrate operations, manage transactions
- ❌ DON'T: Handle HTTP concerns, write SQL queries directly

### Repository Layer (`app/repositories/`)

**Purpose**: Abstract database operations

**Responsibilities**:
- CRUD operations
- Query building
- Database-specific logic
- Relationship handling
- No business logic

**Key Components**:
- `base.py` - Base repository with common CRUD operations
- `booking_repository.py` - Booking data access
- `property_repository.py` - Property data access
- `user_repository.py` - User data access
- `session_repository.py` - Session data access
- `message_repository.py` - Message data access

**Example**:
```python
class BookingRepository(BaseRepository[Booking]):
    def __init__(self):
        super().__init__(Booking)
    
    def get_by_booking_id(self, db: Session, booking_id: str) -> Optional[Booking]:
        """Pure data access - no business logic"""
        return db.query(Booking).filter(
            Booking.booking_id == booking_id
        ).first()
    
    def check_availability(
        self, 
        db: Session, 
        property_id: str, 
        booking_date: datetime, 
        shift_type: str
    ) -> bool:
        """Query logic only"""
        existing = db.query(Booking).filter(
            Booking.property_id == property_id,
            Booking.booking_date == booking_date,
            Booking.shift_type == shift_type,
            Booking.status.in_(["Pending", "Confirmed"])
        ).first()
        return existing is None
```

**Rules**:
- ✅ DO: Database queries, CRUD operations, relationship handling
- ❌ DON'T: Business logic, validation, external API calls

### Integration Layer (`app/integrations/`)

**Purpose**: Communicate with external services

**Responsibilities**:
- API client implementation
- Request/response handling
- Error handling and retries
- Rate limiting
- Authentication

**Key Components**:
- `whatsapp.py` - WhatsApp Business API client
- `cloudinary.py` - Cloudinary media service client
- `gemini.py` - Google Gemini AI client

**Example**:
```python
class WhatsAppClient:
    def __init__(self):
        self.token = settings.META_ACCESS_TOKEN
        self.phone_number_id = settings.META_PHONE_NUMBER_ID
        self.base_url = f"https://graph.facebook.com/v23.0/{self.phone_number_id}"
    
    async def send_message(self, recipient: str, message: str) -> Dict:
        """External API communication"""
        headers = {"Authorization": f"Bearer {self.token}"}
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
                headers=headers,
                timeout=10.0
            )
            return response.json()
```

**Rules**:
- ✅ DO: External API calls, error handling, retries
- ❌ DON'T: Business logic, database operations

### Core Layer (`app/core/`)

**Purpose**: Centralized configuration and shared components

**Responsibilities**:
- Environment configuration
- Application constants
- Custom exceptions
- Shared types and enums

**Key Components**:
- `config.py` - Pydantic settings for environment variables
- `constants.py` - Application-wide constants
- `exceptions.py` - Custom exception hierarchy

**Example**:
```python
# config.py
class Settings(BaseSettings):
    SQLALCHEMY_DATABASE_URL: str
    META_ACCESS_TOKEN: str
    GOOGLE_API_KEY: str
    
    class Config:
        env_file = ".env"

settings = Settings()

# exceptions.py
class AppException(Exception):
    """Base exception"""
    pass

class BookingException(AppException):
    """Booking-specific errors"""
    pass
```

### Utils Layer (`app/utils/`)

**Purpose**: Shared utility functions

**Responsibilities**:
- Pure functions (no side effects)
- Reusable logic
- Data transformation
- Validation helpers

**Key Components**:
- `formatters.py` - Message and data formatting
- `validators.py` - Input validation functions
- `date_utils.py` - Date manipulation
- `media_utils.py` - Media URL extraction

**Example**:
```python
def validate_cnic(cnic: str) -> bool:
    """Pure function - no side effects"""
    if not cnic:
        return False
    cleaned = cnic.replace("-", "")
    return len(cleaned) == 13 and cleaned.isdigit()
```

## Design Patterns

### 1. Repository Pattern
Abstracts data access logic from business logic.

**Benefits**:
- Testable (mock repositories in tests)
- Swappable data sources
- Centralized query logic

### 2. Dependency Injection
Dependencies are provided to classes rather than created internally.

**Benefits**:
- Loose coupling
- Easy testing with mocks
- Flexible configuration

**Implementation**:
```python
# FastAPI dependency injection
def get_booking_service(
    booking_repo: BookingRepository = Depends(get_booking_repo)
) -> BookingService:
    return BookingService(booking_repo)

@router.post("/bookings")
async def create_booking(
    service: BookingService = Depends(get_booking_service)
):
    return service.create_booking(...)
```

### 3. Service Layer Pattern
Encapsulates business logic in service classes.

**Benefits**:
- Reusable across different interfaces (API, CLI, etc.)
- Testable in isolation
- Clear business logic location

### 4. Client Pattern
Wraps external API calls in dedicated client classes.

**Benefits**:
- Mockable for testing
- Centralized error handling
- Easy to swap implementations

## Data Flow

### Example: Creating a Booking

```
1. Client Request
   ↓
2. API Layer (web_chat.py)
   - Validates request with Pydantic
   - Extracts data
   ↓
3. Service Layer (booking_service.py)
   - Checks availability via repository
   - Gets pricing via repository
   - Validates business rules
   - Creates booking via repository
   - Sends notifications via notification service
   ↓
4. Repository Layer (booking_repository.py)
   - Executes SQL queries
   - Returns domain objects
   ↓
5. Database
   - Persists data
   ↓
6. Integration Layer (whatsapp.py)
   - Sends WhatsApp notification
   ↓
7. Response flows back up the stack
```

## Database Schema

### Core Entities

**User**
- Stores customer information
- Links to sessions and bookings

**Property**
- Property details and amenities
- Pricing information
- Media (images, videos)

**Booking**
- Booking details and status
- Links user and property
- Tracks payment status

**Message**
- Chat history
- Links to user and session

**Session**
- User session state
- Conversation context

### Relationships

```
User 1──────* Booking
User 1──────* Session
User 1──────* Message

Property 1──────* Booking
Property 1──────* PropertyPricing
Property 1──────* PropertyImage
Property 1──────* PropertyVideo

Session 1──────* Message
```

## Error Handling

### Exception Hierarchy

```
AppException (base)
├── BookingException
├── PaymentException
├── PropertyException
└── IntegrationException
```

### Error Flow

```
Service Layer
  ↓ raises custom exception
API Layer
  ↓ catches and converts to HTTP error
Client
  ↓ receives HTTP error response
```

### Example

```python
# Service
def create_booking(self, ...):
    if not available:
        raise BookingException("Property not available")

# API
try:
    result = service.create_booking(...)
except BookingException as e:
    raise HTTPException(status_code=400, detail=e.message)
```

## Security Considerations

### API Security
- Input validation with Pydantic
- SQL injection prevention via ORM
- Environment-based secrets

### Data Protection
- Sensitive data in environment variables
- No secrets in code
- Secure external API communication

### External Integrations
- Timeout on all external calls
- Retry logic with exponential backoff
- Rate limiting awareness

## Performance Considerations

### Database
- Connection pooling
- Indexed queries
- Lazy loading for relationships

### Caching
- Consider Redis for frequently accessed data
- Cache property details
- Cache pricing information

### Async Operations
- Async for external API calls
- Background tasks for non-critical operations
- Parallel processing where possible

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

### Metrics to Track
- Booking creation rate
- Payment processing time
- External API response times
- Database query performance
- Error rates by type

## Testing Strategy

### Unit Tests
- Test services with mocked repositories
- Test repositories with test database
- Test utilities in isolation

### Integration Tests
- Test API endpoints end-to-end
- Test database operations
- Test external integrations (mocked)

### Test Structure
```
tests/
├── unit/
│   ├── services/
│   ├── repositories/
│   └── utils/
├── integration/
│   ├── api/
│   └── workflows/
└── conftest.py (fixtures)
```

## Deployment Architecture

### Application Components
- FastAPI application server
- PostgreSQL database
- Background task scheduler

### External Dependencies
- WhatsApp Business API
- Cloudinary CDN
- Google Gemini AI

### Scaling Considerations
- Horizontal scaling of API servers
- Database read replicas
- Message queue for background tasks
- CDN for static assets

## Future Enhancements

### Potential Improvements
1. **Caching Layer**: Redis for frequently accessed data
2. **Message Queue**: RabbitMQ/Celery for background tasks
3. **API Versioning**: Support multiple API versions
4. **GraphQL**: Alternative API interface
5. **Microservices**: Split into smaller services if needed
6. **Event Sourcing**: Track all state changes
7. **CQRS**: Separate read and write models

### Scalability Path
1. Add caching layer
2. Implement message queue
3. Add read replicas
4. Consider microservices architecture
5. Implement event-driven architecture

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)

---

**Last Updated**: [Current Date]
**Version**: 2.0 (Post-Refactoring)
