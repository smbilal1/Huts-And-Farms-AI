# Requirements Document

## Introduction

This document outlines the requirements for implementing an automated payment verification system with multiple verification modes. The system will support:

1. **Automated Gmail-based verification** - Reads payment emails from NayaPay/bank and auto-matches to bookings
2. **Web-based admin verification** - Admin reviews bookings via web dashboard (not chat)
3. **Hybrid mode** - Combines both approaches with fallback
4. **Booking expiration with notifications** - Auto-expires unpaid bookings after 15 minutes with customer notification

**Goals:**
- Automate payment verification to reduce manual work
- Provide web-based admin dashboard for payment review
- Support multiple payment verification modes (configurable)
- Maintain backward compatibility with existing booking flow
- Send automated notifications for booking expiration
- Enable easy switching between verification modes via configuration

**Non-Goals:**
- Changing existing booking creation logic
- Modifying database schema for existing tables (only additions)
- Removing manual verification completely (keep as fallback)

---

## Requirements

### Requirement 1: Configuration-Based Verification Modes

**User Story:** As a system administrator, I want to configure which payment verification mode to use, so that I can easily switch between automated, manual, or hybrid verification without code changes.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL load verification mode from configuration
2. WHEN verification mode is set to "automated" THEN the system SHALL use Gmail-based verification only
3. WHEN verification mode is set to "manual" THEN the system SHALL use web-based admin verification only
4. WHEN verification mode is set to "hybrid" THEN the system SHALL try automated first, then fallback to manual
5. WHEN configuration is changed THEN the system SHALL apply new mode without code deployment
6. WHEN an invalid mode is configured THEN the system SHALL default to "manual" mode and log a warning

---

### Requirement 2: Gmail Integration for Payment Detection

**User Story:** As a system, I want to automatically read payment notification emails from Gmail, so that I can detect payments without manual intervention.

#### Acceptance Criteria

1. WHEN Gmail API is configured THEN the system SHALL authenticate using OAuth2 credentials
2. WHEN the background job runs THEN it SHALL fetch unread emails from configured payment provider (NayaPay)
3. WHEN a payment email is found THEN it SHALL extract: amount, sender name, sender phone, transaction ID, date
4. WHEN email parsing succeeds THEN it SHALL return structured payment data
5. WHEN email parsing fails THEN it SHALL log the error and skip that email
6. WHEN an email is processed THEN it SHALL be marked as read to prevent duplicate processing
7. WHEN Gmail API is unavailable THEN the system SHALL log error and retry on next cycle

---

### Requirement 3: Automated Payment Matching

**User Story:** As a system, I want to automatically match incoming payments to pending bookings, so that bookings can be confirmed without admin intervention.

#### Acceptance Criteria

1. WHEN payment data is extracted from email THEN the system SHALL search for matching pending bookings
2. WHEN matching bookings THEN it SHALL compare: amount (exact match), booking age (<15 min), customer name (optional), customer phone (optional)
3. WHEN a single booking matches THEN it SHALL auto-confirm the booking
4. WHEN multiple bookings match THEN it SHALL select the most recent one with highest match score
5. WHEN no booking matches THEN it SHALL create an unmatched payment record for admin review
6. WHEN booking is auto-confirmed THEN it SHALL update status from "Pending" to "Confirmed"
7. WHEN booking is auto-confirmed THEN it SHALL save transaction ID and payment method
8. WHEN booking is auto-confirmed THEN it SHALL send confirmation notification to customer

---

### Requirement 4: Web-Based Admin Dashboard for Payment Review

**User Story:** As an admin, I want to review pending payments via a web dashboard, so that I can verify payments visually without using chat commands.

#### Acceptance Criteria

1. WHEN admin accesses the dashboard THEN it SHALL display all bookings with status "Waiting" (payment screenshot received)
2. WHEN a booking is displayed THEN it SHALL show: booking details, customer info, payment screenshot, expected amount
3. WHEN admin clicks "View Details" THEN it SHALL show full booking information and payment screenshot
4. WHEN admin clicks "Confirm" THEN the system SHALL change booking status to "Confirmed" and notify customer
5. WHEN admin clicks "Reject" THEN the system SHALL prompt for rejection reason
6. WHEN admin provides rejection reason THEN the system SHALL change booking status to "Cancelled" and send reason to customer
7. WHEN admin dashboard is accessed THEN it SHALL require authentication
8. WHEN bookings are confirmed/rejected THEN they SHALL be removed from the pending list

---

### Requirement 5: Payment Screenshot Verification Enhancement

**User Story:** As a system, I want to match payment screenshot data with Gmail payment data, so that I can auto-confirm bookings when both sources match.

#### Acceptance Criteria

1. WHEN user submits payment screenshot THEN the system SHALL extract payment information using AI
2. WHEN screenshot data is extracted THEN it SHALL include: amount, sender name, transaction ID, date
3. WHEN screenshot is processed THEN the system SHALL check if matching Gmail payment exists
4. WHEN Gmail payment matches screenshot data THEN the system SHALL auto-confirm booking
5. WHEN Gmail payment doesn't match THEN the system SHALL change status to "Waiting" for admin review
6. WHEN auto-confirmation succeeds THEN the system SHALL notify customer immediately
7. WHEN verification fails THEN the system SHALL log mismatch details for debugging

---

### Requirement 6: Booking Expiration with Customer Notification

**User Story:** As a customer, I want to be notified when my booking expires, so that I know I need to create a new booking if I still want the property.

#### Acceptance Criteria

1. WHEN a booking is created THEN it SHALL have status "Pending" with 15-minute expiration timer
2. WHEN background job runs THEN it SHALL check for bookings older than 15 minutes with status "Pending"
3. WHEN a booking expires THEN it SHALL change status from "Pending" to "Expired"
4. WHEN booking status changes to "Expired" THEN it SHALL send expiration notification to customer
5. WHEN expiration notification is sent THEN it SHALL include: property name, booking date, shift, instructions to rebook
6. WHEN customer is on website THEN notification SHALL be saved to their web chat
7. WHEN customer is on WhatsApp THEN notification SHALL be sent via WhatsApp
8. WHEN booking expires THEN the property SHALL become available for other customers

---

### Requirement 7: Payment Data Storage and Tracking

**User Story:** As a developer, I want payment data properly stored and tracked, so that I can audit payment verification and debug issues.

#### Acceptance Criteria

1. WHEN payment is detected via Gmail THEN it SHALL be stored in a "payments" table
2. WHEN payment screenshot is processed THEN extracted data SHALL be stored with the booking
3. WHEN payment data is stored THEN it SHALL include: source (gmail/screenshot), transaction_id, amount, sender_name, sender_phone, timestamp
4. WHEN booking is confirmed THEN it SHALL reference the payment record
5. WHEN payment cannot be matched THEN it SHALL be stored as "unmatched" for admin review
6. WHEN admin reviews unmatched payment THEN they SHALL be able to manually link it to a booking

---

### Requirement 8: Admin Web Dashboard API Endpoints

**User Story:** As a frontend developer, I want REST API endpoints for the admin dashboard, so that I can build the admin interface.

#### Acceptance Criteria

1. WHEN admin requests pending verifications THEN API SHALL return list of bookings with status "Waiting"
2. WHEN admin requests booking details THEN API SHALL return full booking info, customer info, and payment screenshot URL
3. WHEN admin confirms booking THEN API SHALL accept booking_id and update status to "Confirmed"
4. WHEN admin rejects booking THEN API SHALL accept booking_id and rejection_reason
5. WHEN booking is confirmed via API THEN customer SHALL receive confirmation notification
6. WHEN booking is rejected via API THEN customer SHALL receive rejection notification with reason
7. WHEN API endpoints are called THEN they SHALL require admin authentication
8. WHEN API operations succeed THEN they SHALL return success status and updated booking data

---

### Requirement 9: Notification Service Enhancement

**User Story:** As a customer, I want to receive timely notifications about my booking status, so that I know when my booking is confirmed, rejected, or expired.

#### Acceptance Criteria

1. WHEN booking is auto-confirmed THEN customer SHALL receive confirmation message within 2 minutes
2. WHEN booking is manually confirmed THEN customer SHALL receive confirmation message immediately
3. WHEN booking is rejected THEN customer SHALL receive rejection message with reason
4. WHEN booking expires THEN customer SHALL receive expiration message with rebooking instructions
5. WHEN notification is sent to web user THEN it SHALL be saved to their message history
6. WHEN notification is sent to WhatsApp user THEN it SHALL be sent via WhatsApp API
7. WHEN notification fails THEN the system SHALL log error and retry once

---

### Requirement 10: Verification Mode Switching

**User Story:** As a system administrator, I want to easily switch between verification modes, so that I can adapt to changing business needs without code changes.

#### Acceptance Criteria

1. WHEN verification mode is "automated" THEN admin dashboard SHALL show only unmatched payments
2. WHEN verification mode is "manual" THEN all payment screenshots SHALL go to admin dashboard
3. WHEN verification mode is "hybrid" THEN system SHALL try automated first, fallback to manual if no match
4. WHEN mode is switched THEN existing pending bookings SHALL continue with current mode
5. WHEN mode is switched THEN new bookings SHALL use new mode
6. WHEN configuration is updated THEN system SHALL reload without restart

---

### Requirement 11: Database Schema Enhancements

**User Story:** As a developer, I want proper database schema to support payment tracking, so that all payment data is properly stored and auditable.

#### Acceptance Criteria

1. WHEN system is deployed THEN a "payments" table SHALL exist with fields: payment_id, booking_id, source, transaction_id, amount, sender_name, sender_phone, email_id, screenshot_url, status, created_at
2. WHEN Booking model is updated THEN it SHALL include: payment_id (foreign key), payment_verified_at, verification_method, expiration_notified_at
3. WHEN payment is detected THEN a payment record SHALL be created
4. WHEN booking is confirmed THEN it SHALL link to the payment record
5. WHEN database migrations run THEN they SHALL not break existing data

---

### Requirement 12: Background Jobs Enhancement

**User Story:** As a system, I want background jobs to handle payment checking and booking expiration, so that these processes run automatically without manual triggers.

#### Acceptance Criteria

1. WHEN scheduler starts THEN it SHALL include: Gmail payment checker (every 2 min), Booking expiration job (every 5 min)
2. WHEN Gmail checker runs THEN it SHALL process new payment emails and match to bookings
3. WHEN expiration job runs THEN it SHALL expire old bookings and send notifications
4. WHEN jobs fail THEN they SHALL log errors and continue on next cycle
5. WHEN jobs succeed THEN they SHALL log summary of actions taken
6. WHEN system shuts down THEN scheduler SHALL stop gracefully

---

### Requirement 13: Backward Compatibility

**User Story:** As a system operator, I want the new payment verification system to work alongside existing functionality, so that current operations are not disrupted.

#### Acceptance Criteria

1. WHEN new system is deployed THEN existing booking creation flow SHALL work identically
2. WHEN verification mode is "manual" THEN system SHALL behave like current implementation
3. WHEN admin chat verification is removed THEN existing admin endpoints SHALL still work for other purposes
4. WHEN new features are added THEN existing API contracts SHALL not change
5. WHEN database is migrated THEN existing bookings SHALL remain valid
6. WHEN system runs THEN all existing tests SHALL pass

---

### Requirement 14: Error Handling and Fallbacks

**User Story:** As a system, I want robust error handling and fallback mechanisms, so that payment verification continues even when some components fail.

#### Acceptance Criteria

1. WHEN Gmail API fails THEN system SHALL fallback to manual verification
2. WHEN payment matching fails THEN system SHALL create unmatched payment for admin review
3. WHEN notification sending fails THEN system SHALL log error and retry once
4. WHEN screenshot extraction fails THEN system SHALL fallback to manual admin review
5. WHEN database operation fails THEN system SHALL rollback transaction and log error
6. WHEN any component fails THEN customer SHALL still be able to complete booking via manual verification
