# Test Infrastructure Documentation

## Overview

This directory contains the test infrastructure for the booking system. The tests are organized into unit tests and integration tests, with comprehensive fixtures for mocking external services and database operations.

## Directory Structure

```
tests/
├── __init__.py                 # Package initialization
├── conftest.py                 # Shared pytest fixtures
├── README.md                   # This file
├── unit/                       # Unit tests
│   ├── __init__.py
│   └── test_fixtures.py        # Fixture verification tests
└── integration/                # Integration tests
    ├── __init__.py
    └── test_api_integration.py # API endpoint tests
```

## Test Database

Tests use a SQLite test database (`test_shared.db`) that is created and destroyed for each test function. This ensures test isolation and prevents test interference.

### Database Fixtures

- `test_engine`: Session-scoped database engine
- `test_db_session`: Function-scoped database session (fresh for each test)
- `db_session`: Alias for `test_db_session`

## Sample Data Fixtures

These fixtures provide sample data dictionaries for creating test objects:

- `sample_user_data`: User data dictionary
- `sample_property_data`: Property data dictionary
- `sample_booking_data`: Booking data dictionary
- `sample_pricing_data`: Pricing data dictionary
- `sample_message_data`: Message data dictionary

## Database Model Fixtures

These fixtures create actual database objects in the test database:

- `db_user`: Creates a User in the test database
- `db_property`: Creates a Property in the test database
- `db_booking`: Creates a Booking in the test database
- `db_pricing`: Creates PropertyPricing in the test database

## Mock External Service Fixtures

These fixtures provide mocked versions of external service clients:

### WhatsApp Client Mock
```python
def test_something(mock_whatsapp_client):
    # mock_whatsapp_client.send_message is an AsyncMock
    result = await mock_whatsapp_client.send_message("123", "Hello")
    assert result["success"] is True
```

### Cloudinary Client Mock
```python
def test_something(mock_cloudinary_client):
    # mock_cloudinary_client.upload_base64 is an AsyncMock
    url = await mock_cloudinary_client.upload_base64("base64data")
    assert "cloudinary.com" in url
```

### Gemini Client Mock
```python
def test_something(mock_gemini_client):
    # mock_gemini_client.extract_payment_info is an AsyncMock
    info = await mock_gemini_client.extract_payment_info("image_url")
    assert info["is_payment_screenshot"] is True
```

## Mock Repository Fixtures

These fixtures provide mocked repository instances for testing services:

- `mock_booking_repository`: Mock BookingRepository
- `mock_property_repository`: Mock PropertyRepository
- `mock_user_repository`: Mock UserRepository
- `mock_session_repository`: Mock SessionRepository
- `mock_message_repository`: Mock MessageRepository

### Example Usage
```python
def test_booking_service(mock_booking_repository, mock_property_repository):
    # Setup mock behavior
    mock_booking_repository.check_availability.return_value = True
    mock_property_repository.get_pricing.return_value = Mock(price=5000)
    
    # Create service with mocked dependencies
    service = BookingService(mock_booking_repository, mock_property_repository)
    
    # Test service method
    result = service.create_booking(...)
    
    # Verify mock was called
    mock_booking_repository.check_availability.assert_called_once()
```

## Mock Service Fixtures

These fixtures provide mocked service instances for testing API endpoints:

- `mock_booking_service`: Mock BookingService
- `mock_payment_service`: Mock PaymentService
- `mock_property_service`: Mock PropertyService
- `mock_notification_service`: Mock NotificationService
- `mock_session_service`: Mock SessionService
- `mock_media_service`: Mock MediaService

### Example Usage
```python
def test_api_endpoint(mock_booking_service):
    # Setup mock behavior
    mock_booking_service.create_booking.return_value = {"booking_id": "TEST-123"}
    
    # Test API endpoint with mocked service
    response = client.post("/bookings", json={...})
    
    # Verify
    assert response.status_code == 200
    mock_booking_service.create_booking.assert_called_once()
```

## Utility Fixtures

- `mock_db_session`: Mock database session for unit tests
- `future_date`: Returns a datetime 7 days in the future
- `past_date`: Returns a datetime 7 days in the past

## Running Tests

### Run all tests
```bash
pytest
```

### Run unit tests only
```bash
pytest tests/unit/
```

### Run integration tests only
```bash
pytest tests/integration/
```

### Run with verbose output
```bash
pytest -v
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run specific test file
```bash
pytest tests/unit/test_fixtures.py
```

### Run specific test function
```bash
pytest tests/unit/test_fixtures.py::test_sample_user_data
```

## Writing New Tests

### Unit Test Example

```python
# tests/unit/repositories/test_booking_repository.py
import pytest
from app.repositories.booking_repository import BookingRepository

def test_get_by_booking_id(db_session, db_booking):
    """Test getting booking by booking_id."""
    repo = BookingRepository()
    
    # Test
    result = repo.get_by_booking_id(db_session, db_booking.booking_id)
    
    # Assert
    assert result is not None
    assert result.booking_id == db_booking.booking_id
```

### Service Test Example

```python
# tests/unit/services/test_booking_service.py
import pytest
from unittest.mock import Mock
from app.services.booking_service import BookingService

def test_create_booking(
    mock_booking_repository,
    mock_property_repository,
    mock_user_repository,
    mock_notification_service
):
    """Test creating a booking."""
    # Setup mocks
    mock_user_repository.get_by_id.return_value = Mock(user_id="123", name="Test")
    mock_booking_repository.check_availability.return_value = True
    mock_property_repository.get_pricing.return_value = Mock(price=5000)
    
    # Create service
    service = BookingService(
        mock_booking_repository,
        mock_property_repository,
        mock_user_repository,
        mock_notification_service
    )
    
    # Test
    result = service.create_booking(
        db=Mock(),
        user_id="123",
        property_id="prop-1",
        booking_date=datetime.now(),
        shift_type="Day",
        user_name="Test",
        cnic="1234567890123"
    )
    
    # Assert
    assert "error" not in result
    assert "booking_id" in result
```

### Integration Test Example

```python
# tests/integration/test_booking_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_booking_endpoint(db_user, db_property):
    """Test booking creation endpoint."""
    response = client.post(
        "/api/v1/bookings",
        json={
            "user_id": str(db_user.user_id),
            "property_id": str(db_property.property_id),
            "booking_date": "2024-12-25",
            "shift_type": "Day",
            "user_name": "Test User",
            "cnic": "1234567890123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "booking_id" in data
```

## Best Practices

1. **Test Isolation**: Each test should be independent and not rely on other tests
2. **Use Fixtures**: Leverage fixtures for common setup and teardown
3. **Mock External Services**: Always mock external API calls (WhatsApp, Cloudinary, Gemini)
4. **Test Database**: Use the test database fixtures, never the production database
5. **Descriptive Names**: Use clear, descriptive test function names
6. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification
7. **One Assertion Per Test**: Focus each test on a single behavior
8. **Clean Up**: Fixtures handle cleanup automatically, but be mindful of resources

## Troubleshooting

### Database Locked Error
If you see "database is locked" errors, ensure you're using the function-scoped `test_db_session` fixture which creates a fresh database for each test.

### Import Errors
Make sure you're running tests from the project root directory and that the virtual environment is activated.

### Async Test Issues
For async tests, use `pytest-asyncio` and mark tests with `@pytest.mark.asyncio`:
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

## Coverage Goals

- **Unit Tests**: Aim for >80% code coverage
- **Integration Tests**: Cover all API endpoints and critical workflows
- **Edge Cases**: Test error conditions and boundary cases
- **Happy Path**: Ensure all normal workflows are tested
