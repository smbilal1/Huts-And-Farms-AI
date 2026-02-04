"""
Comprehensive test for booking conflicts.

This test:
1. Creates test bookings in the database
2. Uses the actual list_properties tool (same as agent uses)
3. Verifies conflict detection works correctly
"""

from datetime import datetime
from app.database import SessionLocal
from app.models.booking import Booking
from app.models.user import User
from sqlalchemy import text
import uuid

# Import the actual tool function used by the agent
from app.agents.tools.property_tools import list_properties


def setup_test_user():
    """Create or get a test user."""
    db = SessionLocal()
    
    try:
        # Check if test user exists
        test_user = db.query(User).filter_by(email="test@conflict.com").first()
        
        if not test_user:
            test_user = User(
                user_id=str(uuid.uuid4()),
                name="Test User",
                email="test@conflict.com",
                phone_number="+923001234567"
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            print(f"✓ Created test user: {test_user.user_id}")
        else:
            print(f"✓ Using existing test user: {test_user.user_id}")
        
        return test_user.user_id
    finally:
        db.close()


def setup_test_session(user_id):
    """Create or get a test session."""
    from app.models import Session as SessionModel
    
    db = SessionLocal()
    
    try:
        # Check if test session exists
        test_session = db.query(SessionModel).filter_by(user_id=user_id).first()
        
        if not test_session:
            test_session = SessionModel(
                id=str(uuid.uuid4()),
                user_id=user_id
            )
            db.add(test_session)
            db.commit()
            db.refresh(test_session)
            print(f"✓ Created test session: {test_session.id}")
        else:
            print(f"✓ Using existing test session: {test_session.id}")
        
        return test_session.id
    finally:
        db.close()


def get_property_id():
    """Get a test property ID."""
    db = SessionLocal()
    
    try:
        sql = """
            SELECT property_id, name
            FROM properties
            WHERE type = 'farm' AND city = 'Karachi'
            LIMIT 1
        """
        result = db.execute(text(sql)).first()
        
        if result:
            property_id, name = result
            print(f"✓ Using property: {name} ({property_id})")
            return str(property_id), name
        else:
            print("✗ No properties found!")
            return None, None
    finally:
        db.close()


def clear_test_bookings():
    """Clear any existing test bookings."""
    db = SessionLocal()
    
    try:
        # Delete test bookings
        sql = """
            DELETE FROM bookings
            WHERE user_id IN (
                SELECT user_id FROM users WHERE email = 'test@conflict.com'
            )
        """
        result = db.execute(text(sql))
        db.commit()
        print(f"✓ Cleared {result.rowcount} existing test bookings")
    finally:
        db.close()


def create_test_booking(user_id, property_id, booking_date, shift_type, status="Confirmed"):
    """Create a test booking."""
    db = SessionLocal()
    
    try:
        booking = Booking(
            booking_id=f"TEST-{booking_date.strftime('%Y%m%d')}-{shift_type.replace(' ', '')}",
            user_id=user_id,
            property_id=property_id,
            booking_date=booking_date,
            shift_type=shift_type,
            total_cost=10000.00,
            booking_source="Bot",
            status=status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(booking)
        db.commit()
        
        print(f"✓ Created booking: {booking_date.date()} - {shift_type} ({status})")
        return booking.booking_id
    except Exception as e:
        db.rollback()
        print(f"✗ Failed to create booking: {e}")
        return None
    finally:
        db.close()


def test_property_availability(session_id, date, shift_type, property_name):
    """Test property availability using the actual tool function."""
    date_str = date.strftime("%Y-%m-%d")
    
    print(f"\n  Testing: {date.strftime('%b %d')} ({date.strftime('%A')}) - {shift_type}")
    print(f"  " + "-" * 60)
    
    # Call the actual tool function by invoking it
    result = list_properties.invoke({
        "session_id": session_id,
        "property_type": "farm",
        "city": "Karachi",
        "date": date_str,
        "shift_type": shift_type
    })
    
    # Check if property is in results
    if property_name in result:
        print(f"  ✓ AVAILABLE - Property found in results")
        return True
    elif "No" in result and "available" in result:
        print(f"  ✗ UNAVAILABLE - {result}")
        return False
    else:
        print(f"  ? UNKNOWN - Result: {result[:100]}...")
        return None


def main():
    """Run the comprehensive conflict test."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 22 + "BOOKING CONFLICT TEST" + " " * 35 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    # Setup
    print("=" * 80)
    print("SETUP")
    print("=" * 80)
    
    user_id = setup_test_user()
    session_id = setup_test_session(user_id)
    property_id, property_name = get_property_id()
    
    if not property_id:
        print("Cannot proceed without a property!")
        return
    
    print()
    
    # Clear existing test bookings
    clear_test_bookings()
    print()
    
    # Test Scenario 1: Day booking blocks related shifts
    print("=" * 80)
    print("SCENARIO 1: Day Booking on Feb 13")
    print("=" * 80)
    print("Creating booking: Feb 13, 2026 - Day shift")
    print()
    
    feb_13 = datetime(2026, 2, 13)
    feb_12 = datetime(2026, 2, 12)
    
    create_test_booking(user_id, property_id, feb_13, "Day")
    
    print("\nExpected Results:")
    print("  ✗ Feb 12 Full Night - Should be UNAVAILABLE (extends to Feb 13 Day)")
    print("  ✗ Feb 13 Day - Should be UNAVAILABLE (exact match)")
    print("  ✗ Feb 13 Full Day - Should be UNAVAILABLE (includes Day)")
    print("  ✓ Feb 13 Night - Should be AVAILABLE (different shift)")
    print("  ✓ Feb 13 Full Night - Should be AVAILABLE (starts with Night)")
    
    print("\nActual Results:")
    test_property_availability(session_id, feb_12, "Full Night", property_name)
    test_property_availability(session_id, feb_13, "Day", property_name)
    test_property_availability(session_id, feb_13, "Full Day", property_name)
    test_property_availability(session_id, feb_13, "Night", property_name)
    test_property_availability(session_id, feb_13, "Full Night", property_name)
    
    # Clear for next scenario
    clear_test_bookings()
    print()
    
    # Test Scenario 2: Night booking blocks related shifts
    print("=" * 80)
    print("SCENARIO 2: Night Booking on Feb 13")
    print("=" * 80)
    print("Creating booking: Feb 13, 2026 - Night shift")
    print()
    
    create_test_booking(user_id, property_id, feb_13, "Night")
    
    print("\nExpected Results:")
    print("  ✓ Feb 13 Day - Should be AVAILABLE (different shift)")
    print("  ✗ Feb 13 Night - Should be UNAVAILABLE (exact match)")
    print("  ✗ Feb 13 Full Day - Should be UNAVAILABLE (includes Night)")
    print("  ✗ Feb 13 Full Night - Should be UNAVAILABLE (starts with Night)")
    
    print("\nActual Results:")
    test_property_availability(session_id, feb_13, "Day", property_name)
    test_property_availability(session_id, feb_13, "Night", property_name)
    test_property_availability(session_id, feb_13, "Full Day", property_name)
    test_property_availability(session_id, feb_13, "Full Night", property_name)
    
    # Clear for next scenario
    clear_test_bookings()
    print()
    
    # Test Scenario 3: Full Day booking blocks everything on that date
    print("=" * 80)
    print("SCENARIO 3: Full Day Booking on Feb 13")
    print("=" * 80)
    print("Creating booking: Feb 13, 2026 - Full Day")
    print()
    
    create_test_booking(user_id, property_id, feb_13, "Full Day")
    
    print("\nExpected Results:")
    print("  ✗ Feb 13 Day - Should be UNAVAILABLE (part of Full Day)")
    print("  ✗ Feb 13 Night - Should be UNAVAILABLE (part of Full Day)")
    print("  ✗ Feb 13 Full Day - Should be UNAVAILABLE (exact match)")
    print("  ✗ Feb 13 Full Night - Should be UNAVAILABLE (conflicts with Full Day)")
    
    print("\nActual Results:")
    test_property_availability(session_id, feb_13, "Day", property_name)
    test_property_availability(session_id, feb_13, "Night", property_name)
    test_property_availability(session_id, feb_13, "Full Day", property_name)
    test_property_availability(session_id, feb_13, "Full Night", property_name)
    
    # Clear for next scenario
    clear_test_bookings()
    print()
    
    # Test Scenario 4: Full Night booking blocks multiple dates
    print("=" * 80)
    print("SCENARIO 4: Full Night Booking on Feb 13")
    print("=" * 80)
    print("Creating booking: Feb 13, 2026 - Full Night")
    print("(Full Night = Night on Feb 13 + Day on Feb 14)")
    print()
    
    feb_14 = datetime(2026, 2, 14)
    
    create_test_booking(user_id, property_id, feb_13, "Full Night")
    
    print("\nExpected Results:")
    print("  ✓ Feb 13 Day - Should be AVAILABLE (before Full Night starts)")
    print("  ✗ Feb 13 Night - Should be UNAVAILABLE (part of Full Night)")
    print("  ✗ Feb 13 Full Day - Should be UNAVAILABLE (includes Night)")
    print("  ✗ Feb 13 Full Night - Should be UNAVAILABLE (exact match)")
    print("  ✗ Feb 14 Day - Should be UNAVAILABLE (part of Full Night)")
    print("  ✓ Feb 14 Night - Should be AVAILABLE (after Full Night ends)")
    print("  ✗ Feb 14 Full Day - Should be UNAVAILABLE (includes Day)")
    print("  ✓ Feb 14 Full Night - Should be AVAILABLE (Night 14 + Day 15, no conflict)")
    
    print("\nActual Results:")
    test_property_availability(session_id, feb_13, "Day", property_name)
    test_property_availability(session_id, feb_13, "Night", property_name)
    test_property_availability(session_id, feb_13, "Full Day", property_name)
    test_property_availability(session_id, feb_13, "Full Night", property_name)
    test_property_availability(session_id, feb_14, "Day", property_name)
    test_property_availability(session_id, feb_14, "Night", property_name)
    test_property_availability(session_id, feb_14, "Full Day", property_name)
    test_property_availability(session_id, feb_14, "Full Night", property_name)
    
    # Cleanup
    print()
    print("=" * 80)
    print("CLEANUP")
    print("=" * 80)
    clear_test_bookings()
    
    print()
    print("=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
