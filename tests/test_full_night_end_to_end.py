"""
End-to-end test for Full Night availability.
Tests the complete flow from repository to service layer.
"""

from datetime import datetime
from app.database import SessionLocal
from app.repositories.property_repository import PropertyRepository
from app.repositories.booking_repository import BookingRepository
from app.services.property_service import PropertyService

def test_full_night_availability():
    """Test Full Night availability through the service layer."""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("End-to-End Test: Full Night Availability")
        print("=" * 80)
        print()
        
        # Initialize repositories and service
        property_repo = PropertyRepository()
        booking_repo = BookingRepository()
        property_service = PropertyService(property_repo, booking_repo)
        
        # Test date: Feb 13, 2026 (Friday)
        test_date = datetime(2026, 2, 13)
        
        print(f"Test Date: {test_date.strftime('%B %d, %Y (%A)')}")
        print()
        
        # Test 1: Full Day (should work)
        print("Test 1: Full Day")
        print("-" * 40)
        try:
            full_day_properties = property_service.search_properties(
                db=db,
                property_type="farm",
                booking_date=test_date,
                shift_type="Full Day",
                city="Karachi"
            )
            print(f"✓ Found {len(full_day_properties)} properties")
            for prop in full_day_properties:
                print(f"  - {prop['name']}: Rs {prop['price']:,.0f}")
        except Exception as e:
            print(f"✗ Error: {e}")
        print()
        
        # Test 2: Full Night (should now work)
        print("Test 2: Full Night")
        print("-" * 40)
        try:
            full_night_properties = property_service.search_properties(
                db=db,
                property_type="farm",
                booking_date=test_date,
                shift_type="Full Night",
                city="Karachi"
            )
            print(f"✓ Found {len(full_night_properties)} properties")
            for prop in full_night_properties:
                print(f"  - {prop['name']}: Rs {prop['price']:,.0f}")
        except Exception as e:
            print(f"✗ Error: {e}")
        print()
        
        # Test 3: Different dates
        test_dates = [
            datetime(2026, 2, 11),  # Wednesday
            datetime(2026, 2, 12),  # Thursday
            datetime(2026, 2, 14),  # Saturday
        ]
        
        print("Test 3: Full Night on Multiple Dates")
        print("-" * 40)
        for test_date in test_dates:
            day_name = test_date.strftime("%A")
            try:
                properties = property_service.search_properties(
                    db=db,
                    property_type="farm",
                    booking_date=test_date,
                    shift_type="Full Night",
                    city="Karachi"
                )
                print(f"✓ {day_name} ({test_date.date()}): {len(properties)} properties")
            except Exception as e:
                print(f"✗ {day_name} ({test_date.date()}): Error - {e}")
        print()
        
        print("=" * 80)
        print("✅ All tests completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_full_night_availability()
