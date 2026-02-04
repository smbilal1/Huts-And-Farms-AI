"""
Script to add Full Night pricing entries to all properties.
Sets Full Night price equal to Full Day price for each day of the week.
"""

from app.database import SessionLocal
from sqlalchemy import text
import uuid

def add_full_night_pricing():
    """Add Full Night pricing entries for all properties."""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("Adding Full Night Pricing to All Properties")
        print("=" * 80)
        print()
        
        # Get all properties with their pricing IDs
        sql = """
            SELECT DISTINCT 
                p.property_id,
                p.name,
                pp.pricing_id
            FROM properties p
            JOIN property_pricing pp ON p.property_id = pp.property_id
            ORDER BY p.name
        """
        
        properties = db.execute(text(sql)).fetchall()
        
        print(f"Found {len(properties)} properties to update")
        print()
        
        total_added = 0
        
        for property_id, property_name, pricing_id in properties:
            print(f"Processing: {property_name}")
            
            # Get Full Day pricing for this property
            sql_full_day = """
                SELECT 
                    day_of_week,
                    price
                FROM property_shift_pricing
                WHERE pricing_id = :pricing_id
                AND shift_type = 'Full Day'
                ORDER BY 
                    CASE day_of_week
                        WHEN 'monday' THEN 1
                        WHEN 'tuesday' THEN 2
                        WHEN 'wednesday' THEN 3
                        WHEN 'thursday' THEN 4
                        WHEN 'friday' THEN 5
                        WHEN 'saturday' THEN 6
                        WHEN 'sunday' THEN 7
                    END
            """
            
            full_day_prices = db.execute(text(sql_full_day), {
                "pricing_id": pricing_id
            }).fetchall()
            
            if not full_day_prices:
                print(f"  ⚠️  No Full Day pricing found, skipping")
                continue
            
            added_count = 0
            
            for day_of_week, price in full_day_prices:
                # Check if Full Night pricing already exists
                sql_check = """
                    SELECT 1 FROM property_shift_pricing
                    WHERE pricing_id = :pricing_id
                    AND day_of_week = :day_of_week
                    AND shift_type = 'Full Night'
                """
                
                exists = db.execute(text(sql_check), {
                    "pricing_id": pricing_id,
                    "day_of_week": day_of_week
                }).first()
                
                if exists:
                    print(f"  ✓ {day_of_week.capitalize()}: Full Night already exists (Rs {float(price):,.0f})")
                    continue
                
                # Insert Full Night pricing
                sql_insert = """
                    INSERT INTO property_shift_pricing (id, pricing_id, day_of_week, shift_type, price)
                    VALUES (:id, :pricing_id, :day_of_week, :shift_type, :price)
                """
                
                db.execute(text(sql_insert), {
                    "id": str(uuid.uuid4()),
                    "pricing_id": pricing_id,
                    "day_of_week": day_of_week,
                    "shift_type": "Full Night",
                    "price": price
                })
                
                print(f"  ✓ {day_of_week.capitalize()}: Added Full Night pricing (Rs {float(price):,.0f})")
                added_count += 1
            
            if added_count > 0:
                total_added += added_count
                print(f"  → Added {added_count} Full Night pricing entries")
            
            print()
        
        # Commit all changes
        db.commit()
        
        print("=" * 80)
        print(f"✅ Successfully added {total_added} Full Night pricing entries")
        print("=" * 80)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def verify_full_night_pricing():
    """Verify that Full Night pricing was added correctly."""
    db = SessionLocal()
    
    try:
        print("\n")
        print("=" * 80)
        print("Verification: Checking Full Night Pricing")
        print("=" * 80)
        print()
        
        # Get sample property
        sql = """
            SELECT p.property_id, p.name
            FROM properties p
            WHERE p.type = 'farm' AND p.city = 'Karachi'
            LIMIT 1
        """
        
        result = db.execute(text(sql)).first()
        
        if not result:
            print("No properties found for verification")
            return
        
        property_id, property_name = result
        print(f"Sample Property: {property_name}")
        print()
        
        # Get all pricing for this property
        sql = """
            SELECT 
                psp.day_of_week,
                psp.shift_type,
                psp.price
            FROM property_shift_pricing psp
            JOIN property_pricing pp ON psp.pricing_id = pp.pricing_id
            WHERE pp.property_id = :property_id
            AND psp.shift_type IN ('Full Day', 'Full Night')
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
                psp.shift_type
        """
        
        pricing = db.execute(text(sql), {"property_id": property_id}).fetchall()
        
        print(f"{'Day':<12} {'Full Day':<15} {'Full Night':<15} {'Match':<10}")
        print("-" * 60)
        
        # Group by day
        from collections import defaultdict
        by_day = defaultdict(dict)
        
        for day, shift, price in pricing:
            by_day[day][shift] = float(price)
        
        all_match = True
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            full_day = by_day[day].get('Full Day', 0)
            full_night = by_day[day].get('Full Night', 0)
            match = "✓" if full_day == full_night and full_night > 0 else "✗"
            
            if match == "✗":
                all_match = False
            
            print(f"{day.capitalize():<12} Rs {full_day:>10,.0f}  Rs {full_night:>10,.0f}  {match:<10}")
        
        print()
        if all_match:
            print("✅ All Full Night prices match Full Day prices")
        else:
            print("⚠️  Some Full Night prices don't match or are missing")
        
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def main():
    """Run the script."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "ADD FULL NIGHT PRICING" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    # Add Full Night pricing
    add_full_night_pricing()
    
    # Verify the changes
    verify_full_night_pricing()
    
    print()


if __name__ == "__main__":
    main()
