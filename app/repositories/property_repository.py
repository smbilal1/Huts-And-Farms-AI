"""
Property repository for database operations related to properties.

This module provides data access methods for property-related operations,
including property search, pricing retrieval, and media access.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, text

from app.repositories.base import BaseRepository
from app.models.property import (
    Property,
    PropertyPricing,
    PropertyShiftPricing,
    PropertyImage,
    PropertyVideo,
    PropertyAmenity
)


class PropertyRepository(BaseRepository[Property]):
    """
    Repository for property-related database operations.
    
    Extends BaseRepository to provide property-specific query methods
    for searching properties, retrieving pricing, and accessing media.
    """
    
    def __init__(self):
        """Initialize the property repository with the Property model."""
        super().__init__(Property)
    
    def get_by_id(self, db: Session, id: Any) -> Optional[Property]:
        """
        Retrieve a property by its property_id.
        
        Args:
            db: Database session
            id: Property UUID
            
        Returns:
            Property instance if found, None otherwise
        """
        return db.query(Property).filter(Property.property_id == id).first()
    
    def get_by_name(self, db: Session, name: str) -> Optional[Property]:
        """
        Retrieve a property by its name.
        
        Args:
            db: Database session
            name: Property name (case-insensitive)
            
        Returns:
            Property instance if found, None otherwise
        """
        return db.query(Property).filter(Property.name.ilike(name)).first()
    
    def search_properties(
        self,
        db: Session,
        property_type: str,
        booking_date: datetime,
        shift_type: str,
        city: Optional[str] = "Karachi",
        country: Optional[str] = "Pakistan",
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        max_occupancy: Optional[int] = None,
        include_booked: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search and filter available properties based on criteria.
        
        This method performs a complex query to find properties that match
        the given filters, including availability checks for the specified
        date and shift.
        
        Args:
            db: Database session
            property_type: Type of property ('hut' or 'farm')
            booking_date: Date to check availability for
            shift_type: Shift type ('Day', 'Night', 'Full Day', 'Full Night')
            city: City to filter by (default: 'Karachi')
            country: Country to filter by (default: 'Pakistan')
            min_price: Minimum price filter (optional)
            max_price: Maximum price filter (optional)
            max_occupancy: Maximum occupancy needed (optional)
            include_booked: If True, include already booked properties (default: False)
            
        Returns:
            List of dictionaries containing property information with pricing
        """
        # Calculate day of week from booking date
        day_of_week = booking_date.strftime("%A").lower()
        
        # Build SQL query for properties with pricing
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
        
        # Add price range filters
        if min_price is not None:
            sql += " AND psp.price >= :min_price"
        if max_price is not None:
            sql += " AND psp.price <= :max_price"
        
        params = {
            "city": city,
            "country": country,
            "type": property_type,
            "day_of_week": day_of_week,
            "shift_type": shift_type
        }
        
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price
        
        result = db.execute(text(sql), params).fetchall()
        
        available_properties = []
        
        for prop in result:
            property_id, name, city, occupancy, price = prop
            
            # Occupancy check (add buffer of 10 as per existing logic)
            effective_occupancy = occupancy + 10
            if max_occupancy and (max_occupancy > effective_occupancy):
                continue
            
            # Check if property is already booked (unless include_booked is True)
            if not include_booked:
                # Use complex conflict checking based on shift type
                from datetime import timedelta
                
                is_available = True
                
                if shift_type == "Full Day":
                    # Full Day = Day + Night on same date
                    # Conflicts with: Day, Night, Full Day, Full Night on same date
                    # Also conflicts with: Full Night on previous date (extends to current Day)
                    prev_date = (booking_date - timedelta(days=1)).date()
                    
                    # Check same date
                    booking_sql_same = """
                        SELECT 1 FROM bookings
                        WHERE property_id = :pid 
                        AND booking_date = :date
                        AND shift_type IN ('Day', 'Night', 'Full Day', 'Full Night')
                        AND status IN ('Pending', 'Confirmed')
                    """
                    booking_same = db.execute(text(booking_sql_same), {
                        "pid": property_id,
                        "date": booking_date.date()
                    }).first()
                    
                    # Check previous date for Full Night
                    booking_sql_prev = """
                        SELECT 1 FROM bookings
                        WHERE property_id = :pid 
                        AND booking_date = :prev_date
                        AND shift_type = 'Full Night'
                        AND status IN ('Pending', 'Confirmed')
                    """
                    booking_prev = db.execute(text(booking_sql_prev), {
                        "pid": property_id,
                        "prev_date": prev_date
                    }).first()
                    
                    if booking_same or booking_prev:
                        is_available = False
                        
                elif shift_type == "Full Night":
                    # Full Night = Night on booking_date + Day on next_date
                    next_date = (booking_date + timedelta(days=1)).date()
                    
                    # Check booking_date for Night, Full Day, Full Night
                    booking_sql_same = """
                        SELECT 1 FROM bookings
                        WHERE property_id = :pid 
                        AND booking_date = :date
                        AND shift_type IN ('Night', 'Full Day', 'Full Night')
                        AND status IN ('Pending', 'Confirmed')
                    """
                    booking_same = db.execute(text(booking_sql_same), {
                        "pid": property_id,
                        "date": booking_date.date()
                    }).first()
                    
                    # Check next_date for Day, Full Day, Full Night
                    booking_sql_next = """
                        SELECT 1 FROM bookings
                        WHERE property_id = :pid 
                        AND booking_date = :next_date
                        AND shift_type IN ('Day', 'Full Day', 'Full Night')
                        AND status IN ('Pending', 'Confirmed')
                    """
                    booking_next = db.execute(text(booking_sql_next), {
                        "pid": property_id,
                        "next_date": next_date
                    }).first()
                    
                    if booking_same or booking_next:
                        is_available = False
                        
                elif shift_type == "Day":
                    # Day conflicts with: Day, Full Day on same date, Full Night on previous date
                    prev_date = (booking_date - timedelta(days=1)).date()
                    
                    # Check same date
                    booking_sql_same = """
                        SELECT 1 FROM bookings
                        WHERE property_id = :pid 
                        AND booking_date = :date
                        AND shift_type IN ('Day', 'Full Day')
                        AND status IN ('Pending', 'Confirmed')
                    """
                    booking_same = db.execute(text(booking_sql_same), {
                        "pid": property_id,
                        "date": booking_date.date()
                    }).first()
                    
                    # Check previous date for Full Night
                    booking_sql_prev = """
                        SELECT 1 FROM bookings
                        WHERE property_id = :pid 
                        AND booking_date = :prev_date
                        AND shift_type = 'Full Night'
                        AND status IN ('Pending', 'Confirmed')
                    """
                    booking_prev = db.execute(text(booking_sql_prev), {
                        "pid": property_id,
                        "prev_date": prev_date
                    }).first()
                    
                    if booking_same or booking_prev:
                        is_available = False
                        
                elif shift_type == "Night":
                    # Night conflicts with: Night, Full Day, Full Night on same date
                    booking_sql = """
                        SELECT 1 FROM bookings
                        WHERE property_id = :pid 
                        AND booking_date = :date
                        AND shift_type IN ('Night', 'Full Day', 'Full Night')
                        AND status IN ('Pending', 'Confirmed')
                    """
                    booking = db.execute(text(booking_sql), {
                        "pid": property_id,
                        "date": booking_date.date()
                    }).first()
                    
                    if booking:
                        is_available = False
                
                if not is_available:
                    continue  # Skip already booked properties
            
            available_properties.append({
                "property_id": str(property_id),
                "name": name,
                "city": city,
                "max_occupancy": occupancy,
                "shift_type": shift_type,
                "price": float(price)
            })
        
        return available_properties
    
    def get_pricing(
        self,
        db: Session,
        property_id: str,
        booking_date: datetime,
        shift_type: str
    ) -> Optional[PropertyShiftPricing]:
        """
        Get pricing for a specific property, date, and shift.
        
        Args:
            db: Database session
            property_id: Property UUID
            booking_date: Date to get pricing for
            shift_type: Shift type ('Day', 'Night', 'Full Day', 'Full Night')
            
        Returns:
            PropertyShiftPricing instance if found, None otherwise
        """
        # Calculate day of week from booking date
        day_of_week = booking_date.strftime("%A").lower()
        
        pricing = (
            db.query(PropertyShiftPricing)
            .join(PropertyPricing)
            .filter(
                and_(
                    PropertyPricing.property_id == property_id,
                    PropertyShiftPricing.day_of_week == day_of_week,
                    PropertyShiftPricing.shift_type == shift_type
                )
            )
            .first()
        )
        
        return pricing
    
    def get_all_pricing(
        self,
        db: Session,
        property_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all pricing information for a property.
        
        Args:
            db: Database session
            property_id: Property UUID
            
        Returns:
            List of dictionaries containing day, shift, and price information
        """
        sql = """
            SELECT psp.day_of_week, psp.shift_type, psp.price
            FROM property_pricing pp
            JOIN property_shift_pricing psp ON pp.pricing_id = psp.pricing_id
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
        
        results = db.execute(text(sql), {"property_id": property_id}).fetchall()
        
        pricing_list = []
        for day_of_week, shift_type, price in results:
            pricing_list.append({
                "day_of_week": day_of_week,
                "shift_type": shift_type,
                "price": float(price)
            })
        
        return pricing_list
    
    def get_images(
        self,
        db: Session,
        property_id: str
    ) -> List[str]:
        """
        Get all image URLs for a property.
        
        Args:
            db: Database session
            property_id: Property UUID
            
        Returns:
            List of image URLs
        """
        sql = """
            SELECT DISTINCT pi.image_url 
            FROM property_images pi
            WHERE pi.property_id = :property_id
            AND pi.image_url IS NOT NULL
            AND pi.image_url != ''
        """
        
        result = db.execute(text(sql), {"property_id": property_id}).fetchall()
        image_urls = [row[0].strip() for row in result if row[0] and row[0].strip()]
        
        return image_urls
    
    def get_videos(
        self,
        db: Session,
        property_id: str
    ) -> List[str]:
        """
        Get all video URLs for a property.
        
        Args:
            db: Database session
            property_id: Property UUID
            
        Returns:
            List of video URLs
        """
        sql = """
            SELECT DISTINCT pv.video_url 
            FROM property_videos pv
            WHERE pv.property_id = :property_id
            AND pv.video_url IS NOT NULL
            AND pv.video_url != ''
        """
        
        result = db.execute(text(sql), {"property_id": property_id}).fetchall()
        video_urls = [row[0].strip() for row in result if row[0] and row[0].strip()]
        
        return video_urls
    
    def get_amenities(
        self,
        db: Session,
        property_id: str
    ) -> List[Dict[str, str]]:
        """
        Get all amenities for a property.
        
        Args:
            db: Database session
            property_id: Property UUID
            
        Returns:
            List of dictionaries containing amenity type and value
        """
        sql = """
            SELECT pa.type, pa.value 
            FROM property_amenities pa
            WHERE pa.property_id = :property_id
        """
        
        results = db.execute(text(sql), {"property_id": property_id}).fetchall()
        
        amenities = []
        seen = set()
        for amenity_type, amenity_value in results:
            if amenity_type and amenity_value:
                amenity_key = f"{amenity_type}:{amenity_value}"
                if amenity_key not in seen:
                    amenities.append({
                        "type": amenity_type,
                        "value": amenity_value
                    })
                    seen.add(amenity_key)
        
        return amenities
    
    def get_property_details(
        self,
        db: Session,
        property_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive property details including basic info, pricing, and amenities.
        
        Args:
            db: Database session
            property_id: Property UUID
            
        Returns:
            Dictionary containing all property information, or None if not found
        """
        # Get basic property info
        sql = """
            SELECT p.name, p.description, p.city, p.country, p.max_occupancy, p.address
            FROM properties p
            WHERE p.property_id = :property_id
        """
        
        result = db.execute(text(sql), {"property_id": property_id}).first()
        
        if not result:
            return None
        
        name, description, city, country, max_occupancy, address = result
        
        # Get pricing, amenities
        pricing = self.get_all_pricing(db, property_id)
        amenities = self.get_amenities(db, property_id)
        
        return {
            "property_id": property_id,
            "name": name,
            "description": description,
            "city": city,
            "country": country,
            "max_occupancy": max_occupancy,
            "address": address,
            "pricing": pricing,
            "amenities": amenities
        }
