# Implementation Plan

This document outlines the step-by-step tasks for refactoring the booking system into a modular architecture. Tasks are organized by phase and designed to be implemented incrementally with testing at each step.

---

## Phase 1: Core Configuration & Constants

- [x] 1. Create core configuration module





  - Create `app/core/__init__.py`
  - Create `app/core/config.py` with Pydantic Settings class
  - Define all environment variables (DATABASE_URL, API keys, etc.)
  - Add validation for required settings
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Create constants module





  - Create `app/core/constants.py`
  - Move EASYPAISA_NUMBER constant
  - Move WEB_ADMIN_USER_ID constant
  - Move VERIFICATION_WHATSAPP constant
  - Add any other hardcoded values
  - _Requirements: 1.3_

- [x] 3. Update existing imports to use core config





  - Replace `os.getenv()` calls in `app/main.py`
  - Replace `os.getenv()` calls in `app/database.py`
  - Replace `os.getenv()` calls in `app/routers/`
  - Replace `os.getenv()` calls in `tools/`
  - Replace `os.getenv()` calls in `app/agent/`
  - _Requirements: 1.2_

- [x] 4. Test core configuration





  - Verify application starts without errors
  - Verify all environment variables are loaded
  - Verify missing variables raise clear errors
  - _Requirements: 1.4, 10.7_

---

## Phase 2: Database Models Separation

- [x] 5. Split models into domain files






- [x] 5.1 Create user models file

  - Create `app/models/user.py`
  - Move `User` model from `app/chatbot/models.py`
  - Move `Session` model from `app/chatbot/models.py`
  - Keep all relationships intact
  - _Requirements: 2.1, 2.2_


- [x] 5.2 Create property models file

  - Create `app/models/property.py`
  - Move `Property` model
  - Move `PropertyPricing` model
  - Move `PropertyShiftPricing` model
  - Move `PropertyImage` model
  - Move `PropertyVideo` model
  - Move `PropertyAmenity` model
  - Move `Owner` model
  - Move `OwnerProperty` model
  - Keep all relationships intact
  - _Requirements: 2.1, 2.2_


- [x] 5.3 Create booking models file

  - Create `app/models/booking.py`
  - Move `Booking` model
  - Keep all relationships intact
  - _Requirements: 2.1, 2.2_


- [x] 5.4 Create message models file

  - Create `app/models/message.py`
  - Move `Message` model
  - Move `ImageSent` model
  - Move `VideoSent` model
  - Keep all relationships intact
  - _Requirements: 2.1, 2.2_


- [x] 5.5 Create models __init__ file

  - Create `app/models/__init__.py`
  - Import all models for backward compatibility
  - Export all models in `__all__`
  - _Requirements: 2.3, 2.4_

- [x] 6. Update model imports across codebase





  - Update imports in `app/routers/`
  - Update imports in `tools/`
  - Update imports in `app/agent/`
  - Update imports in `app/scheduler.py`
  - _Requirements: 2.3_

- [x] 7. Test model separation





  - Verify application starts without errors
  - Verify all relationships work correctly
  - Verify no database schema changes required
  - Run existing tests to ensure nothing broke
  - _Requirements: 2.4, 2.5, 10.7_

---

## Phase 3: Repository Layer

- [x] 8. Create base repository





  - Create `app/repositories/__init__.py`
  - Create `app/repositories/base.py`
  - Implement `BaseRepository` generic class
  - Add CRUD methods: `get_by_id`, `get_all`, `create`, `update`, `delete`
  - _Requirements: 3.1, 3.2, 3.4_

- [x] 9. Create booking repository





  - Create `app/repositories/booking_repository.py`
  - Extend `BaseRepository[Booking]`
  - Implement `get_by_booking_id()`
  - Implement `get_user_bookings()`
  - Implement `check_availability()`
  - Implement `update_status()`
  - Implement `get_pending_bookings()`
  - Implement `get_expired_bookings()`
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 10. Create property repository





  - Create `app/repositories/property_repository.py`
  - Extend `BaseRepository[Property]`
  - Implement `get_by_name()`
  - Implement `search_properties()` with filters
  - Implement `get_pricing()` for date and shift
  - Implement `get_images()`
  - Implement `get_videos()`
  - Implement `get_amenities()`
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 11. Create user repository





  - Create `app/repositories/user_repository.py`
  - Extend `BaseRepository[User]`
  - Implement `get_by_phone()`
  - Implement `get_by_email()`
  - Implement `get_by_cnic()`
  - Implement `create_or_get()`
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 12. Create session repository





  - Create `app/repositories/session_repository.py`
  - Extend `BaseRepository[Session]`
  - Implement `get_by_user_id()`
  - Implement `create_or_get()`
  - Implement `update_session_data()`
  - Implement `get_inactive_sessions()`
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 13. Create message repository



  - Create `app/repositories/message_repository.py`
  - Extend `BaseRepository[Message]`
  - Implement `get_user_messages()`
  - Implement `get_chat_history()`
  - Implement `save_message()`
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ]* 14. Write repository unit tests
  - Test `BookingRepository` methods
  - Test `PropertyRepository` methods
  - Test `UserRepository` methods
  - Test `SessionRepository` methods
  - Test `MessageRepository` methods
  - Use test database fixtures
  - _Requirements: 3.6, 11.2, 11.4, 11.5_

---

## Phase 4: Integration Clients

- [x] 15. Create WhatsApp integration client





  - Create `app/integrations/__init__.py`
  - Create `app/integrations/whatsapp.py`
  - Implement `WhatsAppClient` class
  - Implement `send_message()` method
  - Implement `send_media()` method
  - Add error handling and retries
  - Load config from `core.config`
  - _Requirements: 6.1, 6.2, 6.3, 6.6, 6.7_

- [x] 16. Create Cloudinary integration client





  - Create `app/integrations/cloudinary.py`
  - Implement `CloudinaryClient` class
  - Implement `upload_base64()` method
  - Implement `upload_url()` method
  - Add error handling
  - Load config from `core.config`
  - _Requirements: 6.1, 6.2, 6.4, 6.6, 6.7_

- [x] 17. Create Gemini integration client





  - Create `app/integrations/gemini.py`
  - Implement `GeminiClient` class
  - Implement `extract_payment_info()` method
  - Implement prompt generation
  - Implement response parsing
  - Add error handling
  - Load config from `core.config`
  - _Requirements: 6.1, 6.2, 6.5, 6.6, 6.7_

- [ ]* 18. Write integration client tests
  - Mock WhatsApp API responses
  - Mock Cloudinary API responses
  - Mock Gemini API responses
  - Test error handling
  - _Requirements: 6.7, 11.2, 11.4, 11.6_

---

## Phase 5: Service Layer

- [x] 19. Create booking service





  - Create `app/services/__init__.py`
  - Create `app/services/booking_service.py`
  - Implement `BookingService` class
  - Implement `create_booking()` method
  - Implement `confirm_booking()` method
  - Implement `cancel_booking()` method
  - Implement `get_user_bookings()` method
  - Implement `check_booking_status()` method
  - Add transaction management
  - Add validation logic
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 20. Create payment service





  - Create `app/services/payment_service.py`
  - Implement `PaymentService` class
  - Implement `process_payment_screenshot()` method
  - Implement `process_payment_details()` method
  - Implement `verify_payment()` method
  - Implement `get_payment_instructions()` method
  - Use `GeminiClient` for screenshot analysis
  - Use `CloudinaryClient` for image upload
  - Add validation logic
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 21. Create property service





  - Create `app/services/property_service.py`
  - Implement `PropertyService` class
  - Implement `search_properties()` method
  - Implement `get_property_details()` method
  - Implement `get_property_images()` method
  - Implement `get_property_videos()` method
  - Implement `check_availability()` method
  - Add business logic for filtering
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 22. Create notification service





  - Create `app/services/notification_service.py`
  - Implement `NotificationService` class
  - Implement `notify_admin_payment_received()` method
  - Implement `notify_customer_payment_received()` method
  - Implement `notify_booking_confirmed()` method
  - Implement `notify_booking_cancelled()` method
  - Use `WhatsAppClient` for WhatsApp notifications
  - Handle web vs WhatsApp routing
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 23. Create session service





  - Create `app/services/session_service.py`
  - Implement `SessionService` class
  - Implement `get_or_create_session()` method
  - Implement `update_session_data()` method
  - Implement `clear_session()` method
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 24. Create media service





  - Create `app/services/media_service.py`
  - Implement `MediaService` class
  - Implement `upload_image()` method
  - Implement `extract_media_urls()` method
  - Implement `remove_media_links()` method
  - Use `CloudinaryClient`
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [ ]* 25. Write service unit tests
  - Test `BookingService` with mocked repositories
  - Test `PaymentService` with mocked clients
  - Test `PropertyService` with mocked repositories
  - Test `NotificationService` with mocked clients
  - Test `SessionService` with mocked repositories
  - Test `MediaService` with mocked clients
  - _Requirements: 4.7, 11.2, 11.4, 11.6_

---

## Phase 6: Utility Functions

- [x] 26. Create utility modules





  - Create `app/utils/__init__.py`
  - Create `app/utils/formatters.py`
  - Create `app/utils/validators.py`
  - Create `app/utils/date_utils.py`
  - Create `app/utils/media_utils.py`
  - _Requirements: 7.1, 7.7_

- [x] 27. Implement formatter utilities





  - Move `formatting()` function from `app/format_message.py`
  - Add WhatsApp markdown formatting functions
  - Add message cleaning functions
  - Ensure pure functions (no side effects)
  - _Requirements: 7.2, 7.6_

- [x] 28. Implement validator utilities





  - Add CNIC validation function
  - Add phone number validation function
  - Add date validation function
  - Add booking ID validation function
  - Ensure pure functions
  - _Requirements: 7.4, 7.6_

- [x] 29. Implement date utilities





  - Add date parsing functions
  - Add date formatting functions
  - Add day-of-week calculation
  - Add date range validation
  - Ensure pure functions
  - _Requirements: 7.3, 7.6_

- [x] 30. Implement media utilities










  - Move `extract_media_urls()` function
  - Move `remove_cloudinary_links()` function
  - Add media type detection
  - Ensure pure functions
  - _Requirements: 7.5, 7.6_

- [ ]* 31. Write utility function tests
  - Test formatter functions
  - Test validator functions
  - Test date utility functions
  - Test media utility functions
  - _Requirements: 7.6, 11.2_

---

## Phase 7: API Layer Refactoring

- [x] 32. Create API dependencies module





  - Create `app/api/__init__.py`
  - Create `app/api/dependencies.py`
  - Implement repository dependency functions
  - Implement service dependency functions
  - Implement integration client dependency functions
  - Use FastAPI `Depends()`
  - _Requirements: 5.4, 5.5_

- [x] 33. Refactor web chat endpoints





  - Create `app/api/v1/__init__.py`
  - Create `app/api/v1/web_chat.py`
  - Move `/web-chat/send-message` endpoint
  - Move `/web-chat/send-image` endpoint
  - Move `/web-chat/history` endpoint
  - Move `/web-chat/session-info` endpoint
  - Move `/web-chat/clear-session` endpoint
  - Refactor to use services via dependency injection
  - Keep only HTTP handling in routes
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [x] 34. Refactor webhook endpoints





  - Create `app/api/v1/webhooks.py`
  - Move `/meta-webhook` GET endpoint (verification)
  - Move `/meta-webhook` POST endpoint (message handling)
  - Refactor to use services via dependency injection
  - Keep only HTTP handling in routes
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [x] 35. Refactor admin endpoints





  - Create `app/api/v1/admin.py`
  - Move `/web-chat/admin/notifications` endpoint
  - Add admin message handling endpoint
  - Refactor to use services via dependency injection
  - Keep only HTTP handling in routes
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [x] 36. Update main.py to use new API structure





  - Update router imports in `app/main.py`
  - Include new API routers
  - Remove old router imports
  - Verify all endpoints are registered
  - _Requirements: 5.7_

- [x] 37. Write API integration tests





  - Test web chat endpoints end-to-end
  - Test webhook endpoints end-to-end
  - Test admin endpoints end-to-end
  - Verify responses match original behavior
  - _Requirements: 5.7, 10.1, 10.2, 11.3, 11.4_

---

## Phase 8: Agent Tools Refactoring

- [x] 38. Organize agent tools by domain





  - Create `app/agents/tools/__init__.py`
  - Create `app/agents/tools/booking_tools.py`
  - Create `app/agents/tools/property_tools.py`
  - Create `app/agents/tools/payment_tools.py`
  - _Requirements: 8.1_

- [x] 39. Refactor booking tools





  - Move `create_booking` tool to `booking_tools.py`
  - Move `check_booking_status` tool
  - Move `get_user_bookings` tool
  - Move `get_payment_instructions` tool
  - Refactor to call `BookingService` methods
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 40. Refactor property tools





  - Move `list_properties` tool to `property_tools.py`
  - Move `get_property_details` tool
  - Move `get_property_images` tool
  - Move `get_property_videos` tool
  - Move `get_property_id_from_name` tool
  - Refactor to call `PropertyService` methods
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 41. Refactor payment tools





  - Move `process_payment_screenshot` tool to `payment_tools.py`
  - Move `process_payment_details` tool
  - Move `confirm_booking_payment` tool
  - Move `reject_booking_payment` tool
  - Refactor to call `PaymentService` methods
  - _Requirements: 8.1, 8.2, 8.3_



- [x] 42. Update agent imports





  - Update imports in `app/agent/booking_agent.py`
  - Update imports in `app/agent/admin_agent.py`
  - Verify agents work identically
  - _Requirements: 8.3, 8.4, 10.5_

- [x] 43. Test agent functionality





  - Test booking agent with refactored tools
  - Test admin agent with refactored tools
  - Verify tool responses match original behavior
  - _Requirements: 8.4, 8.5, 10.5_

---

## Phase 9: Background Tasks Refactoring

- [x] 44. Refactor scheduler setup





  - Create `app/tasks/__init__.py`
  - Create `app/tasks/scheduler.py`
  - Move scheduler initialization code
  - Move `start_cleanup_scheduler()` function
  - Move `stop_cleanup_scheduler()` function
  - Move `get_scheduler_status()` function
  - _Requirements: 9.1, 9.2_

- [x] 45. Refactor cleanup tasks





  - Create `app/tasks/cleanup_tasks.py`
  - Move `cleanup_inactive_sessions()` function
  - Move `expire_pending_bookings()` function
  - Move `scheduled_cleanup()` function
  - Refactor to use service layer methods
  - _Requirements: 9.1, 9.2, 9.3_

- [x] 46. Update scheduler imports





  - Update imports in `app/main.py`
  - Verify scheduler starts correctly
  - Verify scheduled jobs run correctly
  - _Requirements: 9.4_

- [x] 47. Test background tasks





  - Test cleanup tasks execute correctly
  - Test booking expiration works
  - Test scheduler lifecycle
  - _Requirements: 9.4, 9.5, 10.4_

---

## Phase 10: Error Handling & Exceptions

- [x] 48. Create exception hierarchy





  - Create `app/core/exceptions.py`
  - Implement `AppException` base class
  - Implement `BookingException`
  - Implement `PaymentException`
  - Implement `PropertyException`
  - Implement `IntegrationException`
  - _Requirements: 4.6_

- [x] 49. Add exception handling to services





  - Add try-catch blocks in `BookingService`
  - Add try-catch blocks in `PaymentService`
  - Add try-catch blocks in `PropertyService`
  - Raise appropriate custom exceptions
  - _Requirements: 4.6, 5.5_

- [x] 50. Add exception handling to API routes





  - Add exception handlers in web chat routes
  - Add exception handlers in webhook routes
  - Add exception handlers in admin routes
  - Return appropriate HTTP status codes
  - _Requirements: 5.5, 5.6_

---

## Phase 11: Testing Infrastructure

- [x] 51. Setup test infrastructure





  - Create `tests/__init__.py`
  - Create `tests/conftest.py`
  - Create `tests/unit/__init__.py`
  - Create `tests/integration/__init__.py`
  - Setup test database fixtures
  - Setup mock fixtures for external services
  - _Requirements: 11.1, 11.4, 11.5, 11.6_

- [ ]* 52. Write comprehensive unit tests
  - Write tests for all repositories
  - Write tests for all services
  - Write tests for all utilities
  - Achieve >80% code coverage
  - _Requirements: 11.2, 11.4, 11.5, 11.6_

- [ ]* 53. Write integration tests
  - Write tests for all API endpoints
  - Write tests for agent workflows
  - Write tests for background tasks
  - Test end-to-end scenarios
  - _Requirements: 11.3, 11.4, 11.5_

---

## Phase 12: Documentation & Cleanup

- [x] 54. Update project documentation





  - Update README.md with new structure
  - Document architecture in docs/
  - Create developer onboarding guide
  - Document where to add new features
  - _Requirements: 12.1, 12.2, 12.5_

- [x] 55. Create migration guide





  - Document import changes
  - Document new patterns
  - Provide code examples
  - List breaking changes (if any)
  - _Requirements: 12.3_

- [x] 56. Clean up old code





  - Remove old `tools/booking.py` file
  - Remove old `tools/bot_tools.py` file
  - Remove old `app/format_message.py` file
  - Remove old `test.py` file
  - Remove unused imports
  - _Requirements: 10.6_

- [x] 57. Final integration testing





  - Test all API endpoints
  - Test WhatsApp webhook flow
  - Test web chat flow
  - Test admin flow
  - Test booking creation flow
  - Test payment processing flow
  - Verify backward compatibility
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [x] 58. Performance testing




  - Test database query performance
  - Test API response times
  - Test concurrent request handling
  - Optimize if needed
  - _Requirements: 10.7_

- [ ] 59. Deploy and monitor
  - Deploy to staging environment
  - Monitor for errors
  - Verify all functionality works
  - Deploy to production
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_
