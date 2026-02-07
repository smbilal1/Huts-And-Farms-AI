# Booking Details Collection Implementation

## Overview

This document describes the implementation of the `prepare_booking_details` tool that collects and validates user details (name and CNIC) before creating a booking.

## Problem Solved

Previously, the booking flow would fail if users didn't have name/CNIC in the database, requiring manual error handling and re-prompting. The new tool provides a structured, validated workflow that:

1. ✅ Checks if user has name/CNIC before booking
2. ✅ Validates CNIC length (must be 13 digits)
3. ✅ Allows users to confirm or edit existing details
4. ✅ Saves contact details in booking table for reference
5. ✅ Provides clear UI with proper buttons (Submit/Cancel/Edit)

---

## Architecture

### Components Modified/Created

1. **New Tool**: `app/agents/tools/booking_details_tools.py`
   - `prepare_booking_details()` - Main tool for collecting details

2. **Database**:
   - Added `contact_details` column to `bookings` table
   - Stores formatted: "Name: Ahmed Ali, CNIC: 12345-6789012-3"

3. **Models**:
   - Updated `app/models/booking.py` to include `contact_details` field

4. **Services**:
   - Updated `app/services/booking_service.py` to save contact_details

5. **Agent**:
   - Updated `app/agents/booking_agent.py` system prompt
   - Added tool to agent's tool list

6. **Formatter**:
   - Updated `app/core/response_formatter.py` to handle booking details questions

---

## User Flow

### Scenario 1: New User (No Name/CNIC)

```
User: "I want to book White Palace for 15th January"

Agent: Calls prepare_booking_details(session_id)
       ↓
Tool: Checks DB → name=None, cnic=None
      Returns: {
        "ready": false,
        "questions_needed": ["user_name", "cnic"],
        "questions": [...]
      }
       ↓
Formatter: Detects new user → show_cancel=false
           Creates form with ONLY Submit button
       ↓
Frontend: Shows form:
          [Your full name_______]
          [Your CNIC number_____]
          [Submit]  ← Only button
       ↓
User: Fills form → "Ahmed Ali" + "1234567890123"
       ↓
Agent: Calls prepare_booking_details(
         session_id,
         user_name="Ahmed Ali",
         cnic="1234567890123"
       )
       ↓
Tool: Validates CNIC length ✅
      Saves to DB
      Returns: {"ready": true, "confirmed": true}
       ↓
Agent: Calls create_booking() → Booking created!
```

### Scenario 2: Existing User (Has Name/CNIC)

```
User: "Book Seaside Hut for 20th January"

Agent: Calls prepare_booking_details(session_id)
       ↓
Tool: Checks DB → name="Ahmed Ali", cnic="1234567890123"
      Returns: {
        "ready": false,
        "needs_confirmation": true,
        "current_name": "Ahmed Ali",
        "current_cnic": "1234567890123",
        "questions": [{
          "id": "action",
          "options": ["Confirm and Book", "Edit Details"]
        }]
      }
       ↓
Formatter: Creates confirmation form
       ↓
Frontend: Shows:
          👤 Name: Ahmed Ali
          🆔 CNIC: 12345-6789012-3
          
          What would you like to do?
          ○ Confirm and Book
          ○ Edit Details
          [Submit]
       ↓
User: Selects "Confirm and Book"
       ↓
Agent: Calls prepare_booking_details(
         session_id,
         action="Confirm and Book"
       )
       ↓
Tool: Returns: {"ready": true, "confirmed": true}
       ↓
Agent: Calls create_booking() → Booking created!
```

### Scenario 3: User Edits Details

```
User: Selects "Edit Details"
       ↓
Agent: Calls prepare_booking_details(
         session_id,
         action="Edit Details"
       )
       ↓
Tool: Returns: {
        "ready": false,
        "editing": true,
        "questions": [
          {"id": "user_name", "default_value": "Ahmed Ali"},
          {"id": "cnic", "default_value": "1234567890123"}
        ]
      }
       ↓
Formatter: Creates edit form with show_cancel=true
       ↓
Frontend: Shows pre-filled form:
          [Ahmed Ali_____________]  ← Pre-filled
          [1234567890123_________]  ← Pre-filled
          [Submit]  [Cancel]
       ↓
User: Changes CNIC to "9876543210123"
       ↓
Agent: Calls prepare_booking_details(
         session_id,
         user_name="Ahmed Ali",
         cnic="9876543210123"
       )
       ↓
Tool: Validates ✅
      Updates DB
      Returns: {"ready": true, "confirmed": true}
       ↓
Agent: Calls create_booking() → Booking created!
```

---

## Tool API

### `prepare_booking_details()`

**Purpose**: Collect and validate user details before booking

**Parameters**:
- `session_id` (required): Current session ID
- `user_name` (optional): User's full name
- `cnic` (optional): User's CNIC (13 digits)
- `action` (optional): "Confirm and Book" or "Edit Details"

**Returns**:
```python
{
    # Status flags
    "ready": bool,              # True = can call create_booking
    "needs_confirmation": bool, # True = show confirm/edit choice
    "confirmed": bool,          # True = user confirmed
    "editing": bool,            # True = user is editing
    
    # Current values
    "current_name": str,
    "current_cnic": str,
    
    # For formatter
    "main_message": str,
    "questions_needed": list,   # ["user_name", "cnic"]
    "questions": list,          # Question objects
    "validation_errors": list,  # Validation errors
    
    # Error
    "error": str
}
```

**Validation Rules**:
- Name: Minimum 2 characters
- CNIC: Exactly 13 digits, numbers only
- Dashes and spaces automatically removed from CNIC

---

## Database Schema

### Bookings Table

```sql
ALTER TABLE bookings 
ADD COLUMN contact_details TEXT;
```

**Format**: `"Name: Ahmed Ali, CNIC: 12345-6789012-3"`

**Purpose**: 
- Quick reference for admin
- Backup contact info
- Audit trail

---

## Frontend Integration

### Question Types

**New User Form** (show_cancel=false):
```json
{
  "type": "questions",
  "main_message": "To proceed with booking, I need your details.",
  "show_cancel": false,
  "questions": [
    {
      "id": "user_name",
      "text": "Your full name",
      "type": "text",
      "required": true,
      "placeholder": "e.g., Ahmed Ali"
    },
    {
      "id": "cnic",
      "text": "Your CNIC number",
      "type": "text",
      "required": true,
      "placeholder": "13 digits without dashes"
    }
  ]
}
```

**Confirmation Form** (show_cancel=false):
```json
{
  "type": "questions",
  "main_message": "Please confirm your booking details:\n\n👤 Name: Ahmed Ali\n🆔 CNIC: 12345-6789012-3",
  "show_cancel": false,
  "questions": [
    {
      "id": "action",
      "text": "What would you like to do?",
      "type": "choice",
      "required": true,
      "options": ["Confirm and Book", "Edit Details"]
    }
  ]
}
```

**Edit Form** (show_cancel=true):
```json
{
  "type": "questions",
  "main_message": "Edit your details below:",
  "show_cancel": true,
  "cancel_text": "Cancel",
  "questions": [
    {
      "id": "user_name",
      "text": "Your full name",
      "type": "text",
      "required": true,
      "placeholder": "Ahmed Ali",
      "default_value": "Ahmed Ali"
    },
    {
      "id": "cnic",
      "text": "Your CNIC number",
      "type": "text",
      "required": true,
      "placeholder": "1234567890123",
      "default_value": "1234567890123"
    }
  ]
}
```

### Frontend Implementation

```javascript
// Handle default_value for pre-filled inputs
<input 
  type="text" 
  id={question.id}
  defaultValue={question.default_value || ""}
  placeholder={question.placeholder}
  required={question.required}
/>

// Handle show_cancel flag
{response.show_cancel && (
  <button type="button" onClick={handleCancel}>
    {response.cancel_text || "Cancel"}
  </button>
)}
```

---

## Testing

Run tests:
```bash
python tests/test_prepare_booking_details.py
```

Tests cover:
1. ✅ New user flow (no name/CNIC)
2. ✅ Existing user flow (has name/CNIC)
3. ✅ Edit details flow
4. ✅ CNIC validation (length, format)

---

## Agent Workflow

### Critical Rules

1. **ALWAYS call `prepare_booking_details` BEFORE `create_booking`**
2. **NEVER call `create_booking` until `ready=true`**
3. **Follow the tool's response** - show questions/choices to user
4. **Pass user input back** to `prepare_booking_details` for validation

### Example Agent Logic

```python
# Step 1: User wants to book
if user_confirms_booking:
    result = prepare_booking_details(session_id)
    
    # Step 2: Show questions to user
    if not result["ready"]:
        return result["main_message"] + format_questions(result["questions"])
    
    # Step 3: User provides input
    if user_provides_input:
        result = prepare_booking_details(
            session_id,
            user_name=user_input.name,
            cnic=user_input.cnic,
            action=user_input.action
        )
    
    # Step 4: Create booking when ready
    if result["ready"]:
        create_booking(session_id, booking_date, shift_type)
```

---

## Benefits

1. **Validation**: CNIC length checked before booking
2. **User Control**: Can edit or cancel anytime
3. **Data Quality**: Ensures all bookings have contact details
4. **Audit Trail**: contact_details saved in booking table
5. **Better UX**: Clear forms with appropriate buttons
6. **Error Prevention**: Catches issues before booking creation

---

## Future Enhancements

1. Add phone number validation
2. Support multiple CNIC formats (with/without dashes)
3. Add email collection
4. Implement CNIC verification via API
5. Add address collection for delivery

---

## Troubleshooting

### Issue: Tool returns error "Session not found"
**Solution**: Ensure session_id is valid and exists in database

### Issue: CNIC validation fails
**Solution**: Check CNIC is exactly 13 digits, remove dashes/spaces

### Issue: Agent skips prepare_booking_details
**Solution**: Check system prompt includes mandatory workflow rules

### Issue: Frontend doesn't show cancel button
**Solution**: Check formatter is setting show_cancel correctly based on scenario

---

## Related Files

- `app/agents/tools/booking_details_tools.py` - Tool implementation
- `app/agents/booking_agent.py` - Agent integration
- `app/services/booking_service.py` - Booking service
- `app/core/response_formatter.py` - Response formatting
- `app/models/booking.py` - Booking model
- `tests/test_prepare_booking_details.py` - Tests
- `migrations/add_contact_details_to_bookings.sql` - Migration

---

**Last Updated**: February 7, 2026
**Version**: 1.0
