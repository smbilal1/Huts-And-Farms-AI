# Requirements Document

## Introduction

This document outlines the requirements for refactoring the existing booking system codebase into a modular, maintainable architecture. The current codebase has mixed concerns with business logic, database operations, and API handling intertwined in route handlers and tool files. This refactoring will separate concerns into distinct layers (API, Services, Repositories, Integrations) while preserving all existing business logic and functionality.

**Goals:**
- Improve code maintainability and readability
- Enable easier testing through separation of concerns
- Facilitate future feature additions and scaling
- Maintain 100% backward compatibility with existing APIs
- Preserve all business logic without changes

**Non-Goals:**
- Changing any business logic or rules
- Modifying API contracts or endpoints
- Altering database schema
- Changing external integrations behavior

---

## Requirements

### Requirement 1: Core Configuration Layer

**User Story:** As a developer, I want all configuration and constants centralized in one place, so that I can easily manage environment variables and avoid hardcoded values scattered throughout the codebase.

#### Acceptance Criteria

1. WHEN the system starts THEN all environment variables SHALL be loaded from a centralized `core/config.py` module
2. WHEN a developer needs to access configuration THEN they SHALL import from `core.config` instead of using `os.getenv()` directly
3. WHEN constants are needed (like EASYPAISA_NUMBER, WEB_ADMIN_USER_ID) THEN they SHALL be defined in `core/constants.py`
4. IF a configuration value is missing THEN the system SHALL raise a clear error message indicating which variable is missing
5. WHEN configuration is accessed THEN it SHALL use Pydantic Settings for type safety and validation

---

### Requirement 2: Database Models Separation

**User Story:** As a developer, I want database models organized by domain, so that I can easily find and maintain related models without navigating a single large file.

#### Acceptance Criteria

1. WHEN models are organized THEN they SHALL be split into separate files: `booking.py`, `property.py`, `user.py`, `message.py`
2. WHEN models are split THEN all SQLAlchemy relationships SHALL remain intact and functional
3. WHEN a model is imported THEN it SHALL be accessible from `models/__init__.py` for backward compatibility
4. WHEN the application starts THEN all models SHALL be properly registered with SQLAlchemy Base
5. WHEN migrations are run THEN they SHALL work without any schema changes

---

### Requirement 3: Repository Layer Creation

**User Story:** As a developer, I want all database operations isolated in repository classes, so that I can test and modify data access logic independently from business logic.

#### Acceptance Criteria

1. WHEN database operations are needed THEN they SHALL be performed through repository classes
2. WHEN a repository method is called THEN it SHALL accept a database session as a parameter
3. WHEN repositories are created THEN they SHALL include: `BookingRepository`, `PropertyRepository`, `UserRepository`, `MessageRepository`, `SessionRepository`
4. WHEN a repository method executes THEN it SHALL only contain database operations (no business logic)
5. WHEN raw SQL queries exist THEN they SHALL be moved to appropriate repository methods
6. WHEN a repository method fails THEN it SHALL raise appropriate exceptions without handling business logic

---

### Requirement 4: Service Layer Creation

**User Story:** As a developer, I want business logic centralized in service classes, so that I can reuse logic across different endpoints and test it independently.

#### Acceptance Criteria

1. WHEN business logic is needed THEN it SHALL be implemented in service classes
2. WHEN services are created THEN they SHALL include: `BookingService`, `PaymentService`, `PropertyService`, `NotificationService`, `SessionService`, `MediaService`
3. WHEN a service method is called THEN it SHALL orchestrate repository calls and implement business rules
4. WHEN a service handles transactions THEN it SHALL manage database session lifecycle properly
5. WHEN a service needs another service THEN it SHALL use dependency injection
6. WHEN a service method completes THEN it SHALL return domain objects or DTOs (not database models directly)
7. WHEN validation is needed THEN services SHALL validate input before calling repositories

---

### Requirement 5: API Layer Refactoring

**User Story:** As a developer, I want API route handlers to be thin controllers, so that they only handle HTTP concerns and delegate business logic to services.

#### Acceptance Criteria

1. WHEN an API endpoint is called THEN the route handler SHALL only handle HTTP request/response
2. WHEN route handlers are refactored THEN they SHALL delegate all business logic to service classes
3. WHEN routes are organized THEN they SHALL be grouped in `api/v1/` directory: `web_chat.py`, `webhooks.py`, `admin.py`
4. WHEN dependencies are needed THEN they SHALL be injected using FastAPI's `Depends()`
5. WHEN errors occur in services THEN route handlers SHALL catch them and return appropriate HTTP responses
6. WHEN request validation is needed THEN it SHALL use Pydantic models
7. WHEN the API is accessed THEN all existing endpoints SHALL work identically to before refactoring

---

### Requirement 6: Integration Layer Creation

**User Story:** As a developer, I want external service integrations isolated in dedicated client classes, so that I can mock them easily in tests and change implementations without affecting business logic.

#### Acceptance Criteria

1. WHEN external services are called THEN they SHALL be accessed through integration client classes
2. WHEN integrations are created THEN they SHALL include: `WhatsAppClient`, `CloudinaryClient`, `GeminiClient`
3. WHEN a WhatsApp message is sent THEN it SHALL use `WhatsAppClient.send_message()`
4. WHEN an image is uploaded THEN it SHALL use `CloudinaryClient.upload_image()`
5. WHEN payment screenshot analysis is needed THEN it SHALL use `GeminiClient.extract_payment_info()`
6. WHEN integration clients are initialized THEN they SHALL load configuration from `core.config`
7. WHEN integration methods are called THEN they SHALL handle API-specific error handling and retries

---

### Requirement 7: Utility Functions Organization

**User Story:** As a developer, I want utility functions organized by purpose, so that I can easily find and reuse common functionality.

#### Acceptance Criteria

1. WHEN utility functions are needed THEN they SHALL be organized in `utils/` directory
2. WHEN message formatting is needed THEN it SHALL use functions from `utils/formatters.py`
3. WHEN date operations are needed THEN they SHALL use functions from `utils/date_utils.py`
4. WHEN input validation is needed THEN it SHALL use functions from `utils/validators.py`
5. WHEN media URL extraction is needed THEN it SHALL use functions from `utils/media_utils.py`
6. WHEN utility functions are created THEN they SHALL be pure functions (no side effects)
7. WHEN utilities are imported THEN they SHALL be accessible from `utils/__init__.py`

---

### Requirement 8: Agent Tools Refactoring

**User Story:** As a developer, I want AI agent tools organized by domain and using the new service layer, so that agents can leverage the same business logic as API endpoints.

#### Acceptance Criteria

1. WHEN agent tools are organized THEN they SHALL be split into: `booking_tools.py`, `property_tools.py`, `payment_tools.py`
2. WHEN agent tools execute THEN they SHALL call service layer methods instead of direct database operations
3. WHEN tools are refactored THEN all existing tool functionality SHALL remain unchanged
4. WHEN agents use tools THEN they SHALL work identically to before refactoring
5. WHEN new tools are added THEN they SHALL follow the same pattern of calling services

---

### Requirement 9: Background Tasks Refactoring

**User Story:** As a developer, I want background tasks organized separately from scheduler setup, so that I can test and modify task logic independently.

#### Acceptance Criteria

1. WHEN background tasks are organized THEN scheduler setup SHALL be in `tasks/scheduler.py`
2. WHEN cleanup tasks are needed THEN they SHALL be defined in `tasks/cleanup_tasks.py`
3. WHEN tasks execute THEN they SHALL use service layer methods
4. WHEN the scheduler starts THEN all existing scheduled jobs SHALL continue working
5. WHEN tasks are tested THEN they SHALL be testable without running the scheduler

---

### Requirement 10: Backward Compatibility

**User Story:** As a system operator, I want the refactored code to work identically to the current version, so that existing integrations and workflows are not disrupted.

#### Acceptance Criteria

1. WHEN the refactoring is complete THEN all API endpoints SHALL return identical responses
2. WHEN WhatsApp webhooks are received THEN they SHALL be processed identically
3. WHEN bookings are created THEN they SHALL follow the same business rules
4. WHEN payments are processed THEN they SHALL work identically
5. WHEN admin commands are executed THEN they SHALL produce the same results
6. WHEN the database is accessed THEN no schema changes SHALL be required
7. WHEN the application starts THEN it SHALL initialize without errors

---

### Requirement 11: Testing Infrastructure

**User Story:** As a developer, I want a proper testing structure in place, so that I can write unit and integration tests for each layer.

#### Acceptance Criteria

1. WHEN tests are organized THEN they SHALL be in `tests/` directory with `unit/` and `integration/` subdirectories
2. WHEN unit tests are written THEN they SHALL test services and repositories independently
3. WHEN integration tests are written THEN they SHALL test API endpoints end-to-end
4. WHEN tests need fixtures THEN they SHALL be defined in `tests/conftest.py`
5. WHEN tests run THEN they SHALL use a test database (not production)
6. WHEN mocking is needed THEN external integrations SHALL be easily mockable

---

### Requirement 12: Documentation and Migration

**User Story:** As a developer, I want clear documentation of the new architecture, so that I can understand how to work with the refactored codebase.

#### Acceptance Criteria

1. WHEN the refactoring is complete THEN architecture documentation SHALL be updated
2. WHEN new patterns are introduced THEN they SHALL be documented with examples
3. WHEN imports change THEN a migration guide SHALL be provided
4. WHEN the project structure changes THEN README SHALL be updated
5. WHEN developers onboard THEN they SHALL have clear guidelines on where to add new code
