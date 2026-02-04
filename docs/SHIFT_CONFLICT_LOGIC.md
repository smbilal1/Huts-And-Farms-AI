# Shift Conflict Logic Documentation

## Overview
This document explains how booking conflicts are handled for different shift types in the system.

## Shift Definitions

### Time Ranges
- **Day**: 8 AM to 6 PM (same date)
- **Night**: 8 PM to 6 AM (next date)
- **Full Day**: Day + Night on same date (8 AM to 6 AM next day)
- **Full Night**: Night + Day spanning two dates (8 PM to 6 PM next day)

## Conflict Rules

### Full Day Booking
**Spans**: Day shift + Night shift on the SAME date

**Conflicts with**:
- ✗ Day on same date
- ✗ Night on same date
- ✗ Full Day on same date
- ✗ Full Night on same date

**Example**: Full Day on Feb 11
- Blocks: Day/Night/Full Day/Full Night on Feb 11

---

### Full Night Booking
**Spans**: Night shift on booking date + Day shift on NEXT date

**Conflicts with**:
- ✗ Night on same date (booking_date)
- ✗ Full Day on same date (booking_date)
- ✗ Full Night on same date (booking_date)
- ✗ Day on next date (booking_date + 1)
- ✗ Full Day on next date (booking_date + 1)
- ✗ Full Night on next date (booking_date + 1)

**Example**: Full Night on Feb 11
- Blocks: Night/Full Day/Full Night on Feb 11
- Blocks: Day/Full Day/Full Night on Feb 12

---

### Day Booking
**Spans**: Day shift only (8 AM to 6 PM)

**Conflicts with**:
- ✗ Day on same date
- ✗ Full Day on same date
- ✗ Full Night on PREVIOUS date (extends into this Day)

**Example**: Day on Feb 12
- Blocks: Day/Full Day on Feb 12
- Blocked by: Full Night on Feb 11

---

### Night Booking
**Spans**: Night shift only (8 PM to 6 AM next day)

**Conflicts with**:
- ✗ Night on same date
- ✗ Full Day on same date
- ✗ Full Night on same date

**Example**: Night on Feb 11
- Blocks: Night/Full Day/Full Night on Feb 11

---

## Implementation

The conflict logic is implemented in two places:

### 1. `booking_repository.py` - `check_availability()`
Used when creating a new booking to verify the property is available.

### 2. `property_repository.py` - `get_available_properties()`
Used when listing available properties to filter out conflicting bookings.

Both implementations follow the same conflict rules to ensure consistency.

## Testing Scenarios

### Scenario 1: Full Night Booking
```
Given: No existing bookings
When: User books Full Night on Feb 11
Then: 
  - Night on Feb 11 should be blocked
  - Day on Feb 12 should be blocked
  - Full Day on Feb 11 should be blocked
  - Full Day on Feb 12 should be blocked
```

### Scenario 2: Day Booking After Full Night
```
Given: Full Night booking on Feb 11
When: User tries to book Day on Feb 12
Then: Should be blocked (conflict with Full Night's Day component)
```

### Scenario 3: Independent Bookings
```
Given: No existing bookings
When: User books Night on Feb 11
Then: Day on Feb 12 should still be available (no conflict)
```

## Database Query Examples

### Check Full Night Availability (Feb 11)
```sql
-- Check same date (Feb 11) for Night, Full Day, Full Night
SELECT 1 FROM bookings
WHERE property_id = :pid 
AND booking_date = '2026-02-11'
AND shift_type IN ('Night', 'Full Day', 'Full Night')
AND status IN ('Pending', 'Confirmed')

-- Check next date (Feb 12) for Day, Full Day, Full Night
SELECT 1 FROM bookings
WHERE property_id = :pid 
AND booking_date = '2026-02-12'
AND shift_type IN ('Day', 'Full Day', 'Full Night')
AND status IN ('Pending', 'Confirmed')
```

If either query returns a result, the property is NOT available for Full Night on Feb 11.
