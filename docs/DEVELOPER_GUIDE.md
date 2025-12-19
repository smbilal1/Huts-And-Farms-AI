# Developer Onboarding Guide

Welcome to the Booking System development team! This guide will help you get up to speed with the codebase, development practices, and workflows.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Understanding the Codebase](#understanding-the-codebase)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Common Tasks](#common-tasks)
7. [Troubleshooting](#troubleshooting)
8. [Resources](#resources)

## Getting Started

### Prerequisites

Before you begin, ensure you have:
- Python 3.10 or higher
- Git
- PostgreSQL (or use SQLite for local development)
- A code editor (VS Code recommended)
- Basic understanding of FastAPI and SQLAlchemy

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd booking-system
   ```

2. **Install UV package manager**:
   ```bash
   pip install uv
   ```

3. **Create virtual environment**:
   ```bash
   uv venv
   .venv/scripts/activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

4. **Install dependencies**:
   ```bash
   uv pip install -r requirements.txt
   ```

5. **Set up environment variables**:
   Create a `.env` file in the root directory:
   ```env
   # Database
   SQLALCHEMY_DATABASE_URL=sqlite:///./dev.db  # For local development
   
   # WhatsApp (get from team lead)
   META_ACCESS_TOKEN=your_token
   META_PHONE_NUMBER_ID=your_phone_id
   VERIFICATION_WHATSAPP=your_verification_token
   
   # Cloudinary (get from team lead)
   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_api_key
   CLOUDINARY_API_SECRET=your_api_secret
   
   # Google AI (get from team lead)
   GOOGLE_API_KEY=your_gemini_api_key
   
   # Application
   EASYPAISA_NUMBER=03155699929
   WEB_ADMIN_USER_ID=test-admin-id
   ```

6. **Initialize the database**:
   ```bash
   # Run migrations or create tables
   python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
   ```

7. **Run the application**:
   ```bash
   uvicorn app.main:app --reload
   ```

8. **Verify setup**:
   - Open browser to `http://localhost:8000/docs`
   - You should see the Swagger UI with all API endpoints

### IDE Setup (VS Code)

Recommended extensions:
- Python
- Pylance
- Python Test Explorer
- GitLens
- Better Comments

Recommended settings (`.vscode/settings.json`):
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "editor.formatOnSave": true,
  "editor.rulers": [88]
}
```

## Understanding the Codebase

### Architecture Overview

The application follows a **layered architecture**:

```
API Layer → Service Layer → Repository Layer → Database
                ↓
         Integration Layer (External APIs)
```

**Key Principle**: Each layer only talks to the layer directly below it.

### Directory Structure

```
app/
├── api/              # HTTP endpoints (thin controllers)
├── services/         # Business logic (thick services)
├── repositories/     # Database operations (data access)
├── integrations/     # External API clients
├── models/           # Database models (SQLAlchemy)
├── core/             # Configuration and exceptions
├── utils/            # Utility functions
├── agents/           # AI agent tools
└── tasks/            # Background tasks
```

### Key Concepts

#### 1. Dependency Injection

We use FastAPI's dependency injection system:

```python
# Define dependency
def get_booking_service(
    booking_repo: BookingRepository = Depends(get_booking_repo)
) -> BookingService:
    return BookingService(booking_repo)

# Use in endpoint
@router.post("/bookings")
async def create_booking(
    service: BookingService = Depends(get_booking_service)
):
    return service.create_booking(...)
```

#### 2. Repository Pattern

Repositories handle all database operations:

```python
class BookingRepository(BaseRepository[Booking]):
    def get_by_booking_id(self, db: Session, booking_id: str):
        return db.query(Booking).filter(
            Booking.booking_id == booking_id
        ).first()
```

#### 3. Service Layer

Services contain business logic:

```python
class BookingService:
    def create_booking(self, db: Session, **kwargs):
        # Validate
        # Check availability
        # Calculate pricing
        # Create booking
        # Send notifications
        return result
```

### Code Flow Example

Let's trace a booking creation request:

1. **Client** sends POST to `/api/v1/bookings`
2. **API Layer** (`app/api/v1/web_chat.py`):
   - Validates request with Pydantic
   - Calls `booking_service.create_booking()`
3. **Service Layer** (`app/services/booking_service.py`):
   - Checks availability via `booking_repo.check_availability()`
   - Gets pricing via `property_repo.get_pricing()`
   - Creates booking via `booking_repo.create()`
   - Sends notification via `notification_service.notify()`
4. **Repository Layer** (`app/repositories/booking_repository.py`):
   - Executes SQL queries
   - Returns domain objects
5. **Response** flows back up the stack

## Development Workflow

### Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Urgent production fixes

### Feature Development Process

1. **Create a branch**:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Develop your feature**:
   - Write code following the architecture
   - Add tests
   - Update documentation

3. **Test locally**:
   ```bash
   pytest
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add booking cancellation feature"
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Code review**:
   - Address feedback
   - Ensure CI passes

7. **Merge**:
   - Squash and merge to develop

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions or changes
- `refactor:` Code refactoring
- `style:` Code style changes (formatting)
- `chore:` Build process or auxiliary tool changes

Examples:
```
feat: add booking cancellation endpoint
fix: resolve payment verification timeout
docs: update API documentation
test: add unit tests for booking service
refactor: extract validation logic to utils
```

## Coding Standards

### Python Style Guide

Follow [PEP 8](https://pep8.org/) with these specifics:

- **Line length**: 88 characters (Black formatter default)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes for strings
- **Imports**: Organized (standard library, third-party, local)

### Type Hints

Always use type hints:

```python
from typing import Optional, List, Dict

def get_booking(
    db: Session, 
    booking_id: str
) -> Optional[Booking]:
    return db.query(Booking).filter(
        Booking.booking_id == booking_id
    ).first()

def get_user_bookings(
    db: Session, 
    user_id: str
) -> List[Booking]:
    return db.query(Booking).filter(
        Booking.user_id == user_id
    ).all()
```

### Docstrings

Use Google-style docstrings:

```python
def create_booking(
    self, 
    db: Session, 
    user_id: str, 
    property_id: str
) -> Dict:
    """Create a new booking.
    
    Args:
        db: Database session
        user_id: User identifier
        property_id: Property identifier
    
    Returns:
        Dictionary containing booking details
    
    Raises:
        BookingException: If booking cannot be created
    """
    pass
```

### Error Handling

Use custom exceptions:

```python
from app.core.exceptions import BookingException

def create_booking(self, ...):
    if not available:
        raise BookingException(
            message="Property not available",
            code="PROPERTY_NOT_AVAILABLE"
        )
```

### Logging

Use structured logging:

```python
import logging

logger = logging.getLogger(__name__)

def create_booking(self, ...):
    logger.info(f"Creating booking for user {user_id}")
    try:
        # Logic
        logger.info(f"Booking created successfully: {booking_id}")
    except Exception as e:
        logger.error(f"Failed to create booking: {e}", exc_info=True)
        raise
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/              # Unit tests (isolated components)
│   ├── services/
│   ├── repositories/
│   └── utils/
├── integration/       # Integration tests (end-to-end)
│   ├── api/
│   └── workflows/
└── conftest.py        # Shared fixtures
```

### Writing Unit Tests

Test services with mocked dependencies:

```python
from unittest.mock import Mock
import pytest

def test_create_booking_success():
    # Arrange
    booking_repo = Mock()
    property_repo = Mock()
    booking_repo.check_availability.return_value = True
    property_repo.get_pricing.return_value = Mock(price=5000)
    
    service = BookingService(booking_repo, property_repo)
    
    # Act
    result = service.create_booking(
        db=Mock(),
        user_id="test-user",
        property_id="test-property",
        booking_date=datetime(2024, 1, 1),
        shift_type="Day"
    )
    
    # Assert
    assert "error" not in result
    assert "booking_id" in result
    booking_repo.create.assert_called_once()
```

### Writing Integration Tests

Test API endpoints end-to-end:

```python
from fastapi.testclient import TestClient

def test_create_booking_endpoint(client: TestClient):
    # Arrange
    payload = {
        "user_id": "test-user",
        "property_id": "test-property",
        "booking_date": "2024-01-01",
        "shift_type": "Day"
    }
    
    # Act
    response = client.post("/api/v1/bookings", json=payload)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "booking_id" in data
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/services/test_booking_service.py

# Run specific test
pytest tests/unit/services/test_booking_service.py::test_create_booking_success

# Run with verbose output
pytest -v

# Run integration tests only
pytest tests/integration/
```

### Test Coverage

Aim for:
- **80%+ overall coverage**
- **90%+ for services** (business logic)
- **70%+ for repositories** (data access)
- **100% for utilities** (pure functions)

## Common Tasks

### Adding a New API Endpoint

See [docs/ADDING_FEATURES.md](ADDING_FEATURES.md) for detailed instructions.

Quick checklist:
1. Add route in `app/api/v1/`
2. Create/update service in `app/services/`
3. Create/update repository in `app/repositories/`
4. Add tests
5. Update documentation

### Adding a New Database Model

1. **Create model** in `app/models/`:
   ```python
   # app/models/review.py
   from sqlalchemy import Column, String, Integer, ForeignKey
   from app.database import Base
   
   class Review(Base):
       __tablename__ = "reviews"
       
       id = Column(String, primary_key=True)
       booking_id = Column(String, ForeignKey("bookings.id"))
       rating = Column(Integer)
       comment = Column(String)
   ```

2. **Export in `__init__.py`**:
   ```python
   from app.models.review import Review
   __all__ = [..., "Review"]
   ```

3. **Create migration** (if using Alembic)

4. **Create repository**:
   ```python
   class ReviewRepository(BaseRepository[Review]):
       pass
   ```

5. **Add tests**

### Adding an External Integration

1. **Create client** in `app/integrations/`:
   ```python
   class NewServiceClient:
       def __init__(self):
           self.api_key = settings.NEW_SERVICE_API_KEY
       
       async def call_api(self, data: Dict) -> Dict:
           # Implementation
           pass
   ```

2. **Add config** in `app/core/config.py`:
   ```python
   class Settings(BaseSettings):
       NEW_SERVICE_API_KEY: str
   ```

3. **Add dependency** in `app/api/dependencies.py`:
   ```python
   def get_new_service_client() -> NewServiceClient:
       return NewServiceClient()
   ```

4. **Use in service**:
   ```python
   class SomeService:
       def __init__(self, new_service: NewServiceClient):
           self.new_service = new_service
   ```

5. **Add tests with mocks**

### Debugging

#### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Use FastAPI Debug Mode

```bash
uvicorn app.main:app --reload --log-level debug
```

#### Database Query Logging

```python
# In app/database.py
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URL,
    echo=True  # Logs all SQL queries
)
```

#### Interactive Debugging

Use Python debugger:
```python
import pdb; pdb.set_trace()
```

Or VS Code breakpoints (recommended)

## Troubleshooting

### Common Issues

#### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'app'`

**Solution**: Ensure you're running from the project root and virtual environment is activated.

#### Database Connection Errors

**Problem**: `sqlalchemy.exc.OperationalError: could not connect to server`

**Solution**: 
- Check DATABASE_URL in `.env`
- Ensure PostgreSQL is running
- Verify credentials

#### Environment Variable Not Found

**Problem**: `ValidationError: field required`

**Solution**: 
- Check `.env` file exists
- Verify variable names match `config.py`
- Restart application after changes

#### Test Database Issues

**Problem**: Tests failing due to database state

**Solution**:
- Use test fixtures properly
- Ensure test database is isolated
- Clean up after tests

### Getting Help

1. **Check documentation**: Start with this guide and ARCHITECTURE.md
2. **Search codebase**: Look for similar implementations
3. **Ask team**: Use team chat or create a discussion
4. **Create issue**: For bugs or unclear documentation

## Resources

### Internal Documentation
- [Architecture Documentation](ARCHITECTURE.md)
- [Adding Features Guide](ADDING_FEATURES.md)
- [API Documentation](http://localhost:8000/docs) (when running locally)

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

### Learning Path

**Week 1**: Setup and Exploration
- Set up development environment
- Run the application locally
- Explore the codebase
- Read architecture documentation
- Run and understand existing tests

**Week 2**: Small Contributions
- Fix a small bug
- Add a utility function
- Write tests for existing code
- Review pull requests

**Week 3**: Feature Development
- Implement a small feature
- Add API endpoint
- Write comprehensive tests
- Update documentation

**Week 4+**: Independent Work
- Take on larger features
- Mentor new developers
- Contribute to architecture decisions

## Next Steps

1. ✅ Complete initial setup
2. ✅ Run the application locally
3. ✅ Explore the codebase
4. ✅ Read ARCHITECTURE.md
5. ✅ Run the test suite
6. ✅ Make a small change and test it
7. ✅ Review ADDING_FEATURES.md
8. ✅ Pick up your first task!

## Questions?

Don't hesitate to ask! The team is here to help you succeed.

---

**Welcome to the team! Happy coding! 🚀**
