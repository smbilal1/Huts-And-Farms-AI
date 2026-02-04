"""
Test script to diagnose Full Night availability issue.

This script will:
1. Check what pricing entries exist in the database for a sample property
2. Test the query for Full Day (which works)
3. Test the query for Full Night (which fails)
4. Identify the root cause
"""

from datetime import datetime
from app.database import SessionLocal
from sqlalchemy import text

def test_pricing_entries():
    """Check what shift pricing entries exist in the database."""
    db = SessionLocal()
    
    print("=" * 80)
    print("STEP 1: Checking what pricing entries exist in database")
    print("=" * 80)
    
    # Get a sample farm property
    sql = """
        SELECT p.property_id, p.name, p.type
        FROM properties p
        WHERE p.type = 'farm' AND p.city = 'Karachi'
        LIMIT 1
    """
    
    result = db.execute(text(sql)).first()
    
    if not result:
        print("❌ No farm properties found in database!")
        db.close()
        return
    
    property_id, property_name, property_type = result
    print(f"✓ Sample Property: {property_name} (ID: {property_id})")
    print()
    
    # Check what shift pricing entries exist for this property
    sql = """
        SELECT 
            psp.day_of_week,
            psp.shift_type,
            psp.price
        FROM property_shift_pricing psp
        JOIN property_pricing pp ON psp.pricing_id = pp.pricing_id
        WHERE pp.property_id = :property_id
        ORDER BY 
            CASE psp.day_of_week
                WHEN 'monday' THEN 1
                WHEN 'tuesday' THEN 2
                WHEN 'wednesday' THEN 3
                WHEN 'thursday' THEN 4
                WHEN 'friday' THEN 5
                WHEN 'saturday' THEN 6
                WHEN 'sunday' THEN 7
            END,
            CASE psp.shift_type
                WHEN 'Day' THEN 1
                WHEN 'Night' THEN 2
                WHEN 'Full Day' THEN 3
                WHEN 'Full Night' THEN 4
            END
    """
    
    pricing_entries = db.execute(text(sql), {"property_id": property_id}).fetchall()
    
    print(f"Pricing entries for {property_name}:")
    print("-" * 60)
    print(f"{'Day of Week':<15} {'Shift Type':<15} {'Price':<10}")
    print("-" * 60)
    
    has_full_night = False
    has_night = False
    has_day = False
    has_full_day = False
    
    for day, shift, price in pricing_entries:
        print(f"{day:<15} {shift:<15} Rs {float(price):<10,.0f}")
        if shift == "Full Night":
            has_full_night = True
        if shift == "Night":
            has_night = True
        if shift == "Day":
            has_day = True
        if shift == "Full Day":
            has_full_day = True
    
    print()
    print("Summary:")
    print(f"  - Has 'Day' pricing: {'✓' if has_day else '✗'}")
    print(f"  - Has 'Night' pricing: {'✓' if has_night else '✗'}")
    print(f"  - Has 'Full Day' pricing: {'✓' if has_full_day else '✗'}")
    print(f"  - Has 'Full Night' pricing: {'✓' if has_full_night else '✗'}")
    print()
    
    db.close()
    return property_id, property_name, has_full_night, has_night, has_day


def test_full_day_query():
    """Test the query for Full Day (which works)."""
    db = SessionLocal()
    
    print("=" * 80)
    print("STEP 2: Testing Full Day query (Feb 13, 2026 - Thursday)")
    print("=" * 80)
    
    booking_date = datetime(2026, 2, 13)
    day_of_week = booking_date.strftime("%A").lower()  # "thursday"
    
    sql = """
        SELECT DISTINCT p.property_id, p.name, p.city, p.max_occupancy, psp.price
        FROM properties p
        JOIN property_pricing pp ON p.property_id = pp.property_id
        JOIN property_shift_pricing psp ON pp.pricing_id = psp.pricing_id
        WHERE p.city = :city 
        AND p.country = :country 
        AND p.type = :type
        AND psp.day_of_week = :day_of_week
        AND psp.shift_type = :shift_type
    """
    
    params = {
        "city": "Karachi",
        "country": "Pakistan",
        "type": "farm",
        "day_of_week": day_of_week,
        "shift_type": "Full Day"
    }
    
    print(f"Query parameters:")
    print(f"  - day_of_week: {day_of_week}")
    print(f"  - shift_type: Full Day")
    print()
    
    result = db.execute(text(sql), params).fetchall()
    
    print(f"Results: {len(result)} properties found")
    for prop in result[:3]:  # Show first 3
        property_id, name, city, occupancy, price = prop
        print(f"  - {name}: Rs {float(price):,.0f}")
    
    print()
    db.close()


def test_full_night_query():
    """Test the query for Full Night (which fails)."""
    db = SessionLocal()
    
    print("=" * 80)
    print("STEP 3: Testing Full Night query (Feb 13, 2026 - Thursday)")
    print("=" * 80)
    
    booking_date = datetime(2026, 2, 13)
    day_of_week = booking_date.strftime("%A").lower()  # "thursday"
    
    sql = """
        SELECT DISTINCT p.property_id, p.name, p.city, p.max_occupancy, psp.price
        FROM properties p
        JOIN property_pricing pp ON p.property_id = pp.property_id
        JOIN property_shift_pricing psp ON pp.pricing_id = psp.pricing_id
        WHERE p.city = :city 
        AND p.country = :country 
        AND p.type = :type
        AND psp.day_of_week = :day_of_week
        AND psp.shift_type = :shift_type
    """
    
    params = {
        "city": "Karachi",
        "country": "Pakistan",
        "type": "farm",
        "day_of_week": day_of_week,
        "shift_type": "Full Night"
    }
    
    print(f"Query parameters:")
    print(f"  - day_of_week: {day_of_week}")
    print(f"  - shift_type: Full Night")
    print()
    
    result = db.execute(text(sql), params).fetchall()
    
    print(f"Results: {len(result)} properties found")
    if len(result) == 0:
        print("  ❌ No properties found!")
    else:
        for prop in result[:3]:
            property_id, name, city, occupancy, price = prop
            print(f"  - {name}: Rs {float(price):,.0f}")
    
    print()
    db.close()


def test_alternative_full_night_query():
    """Test alternative query that combines Night + Day pricing."""
    db = SessionLocal()
    
    print("=" * 80)
    print("STEP 4: Testing ALTERNATIVE Full Night query")
    print("(Combining Night on Thursday + Day on Friday)")
    print("=" * 80)
    
    from datetime import timedelta
    
    booking_date = datetime(2026, 2, 13)  # Thursday
    next_date = booking_date + timedelta(days=1)  # Friday
    
    day_of_week = booking_date.strftime("%A").lower()  # "thursday"
    next_day_of_week = next_date.strftime("%A").lower()  # "friday"
    
    sql = """
        SELECT DISTINCT 
            p.property_id, 
            p.name, 
            p.city, 
            p.max_occupancy,
            (psp_night.price + psp_day.price) as total_price,
            psp_night.price as night_price,
            psp_day.price as day_price
        FROM properties p
        JOIN property_pricing pp ON p.property_id = pp.property_id
        JOIN property_shift_pricing psp_night ON pp.pricing_id = psp_night.pricing_id
        JOIN property_shift_pricing psp_day ON pp.pricing_id = psp_day.pricing_id
        WHERE p.city = :city 
        AND p.country = :country 
        AND p.type = :type
        AND psp_night.day_of_week = :day_of_week
        AND psp_night.shift_type = 'Night'
        AND psp_day.day_of_week = :next_day_of_week
        AND psp_day.shift_type = 'Day'
    """
    
    params = {
        "city": "Karachi",
        "country": "Pakistan",
        "type": "farm",
        "day_of_week": day_of_week,
        "next_day_of_week": next_day_of_week
    }
    
    print(f"Query parameters:")
    print(f"  - Night on: {day_of_week} (Feb 13)")
    print(f"  - Day on: {next_day_of_week} (Feb 14)")
    print()
    
    result = db.execute(text(sql), params).fetchall()
    
    print(f"Results: {len(result)} properties found")
    if len(result) == 0:
        print("  ❌ No properties found!")
    else:
        for prop in result[:3]:
            property_id, name, city, occupancy, total, night, day = prop
            print(f"  - {name}:")
            print(f"      Night (Thu): Rs {float(night):,.0f}")
            print(f"      Day (Fri): Rs {float(day):,.0f}")
            print(f"      Total: Rs {float(total):,.0f}")
    
    print()
    db.close()


def main():
    """Run all diagnostic tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "FULL NIGHT AVAILABILITY DIAGNOSTIC" + " " * 24 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    try:
        # Step 1: Check pricing entries
        result = test_pricing_entries()
        
        if result:
            property_id, property_name, has_full_night, has_night, has_day = result
            
            # Step 2: Test Full Day (working)
            test_full_day_query()
            
            # Step 3: Test Full Night (failing)
            test_full_night_query()
            
            # Step 4: Test alternative approach
            if has_night and has_day:
                test_alternative_full_night_query()
            
            # Conclusion
            print("=" * 80)
            print("CONCLUSION")
            print("=" * 80)
            
            if has_full_night:
                print("✓ Database HAS 'Full Night' pricing entries")
                print("  → Issue might be in the query logic or conflict checking")
            else:
                print("✗ Database DOES NOT have 'Full Night' pricing entries")
                print("  → Need to calculate Full Night price from Night + Day")
                print()
                if has_night and has_day:
                    print("✓ Database has both 'Night' and 'Day' pricing")
                    print("  → Solution: Modify query to combine Night + Day pricing")
                else:
                    print("✗ Database missing Night or Day pricing")
                    print("  → Need to add pricing entries to database")
            
            print()
        
    except Exception as e:
        print(f"\n❌ Error running diagnostic: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
