"""
Booking repository for database operations related to bookings.

This module provides data access methods for booking-related operations,
including CRUD operations, availability checks, and status management.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, text

from app.repositories.base import BaseRepository
from app.models.booking import Booking


class BookingRepository(BaseRepository[Booking]):
    """
    Repository for booking-related database operations.
    
    Extends BaseRepository to provide booking-specific query methods
    for managing property bookings, checking availability, and tracking
    booking status.
    """
    
    def __init__(self):
        """Initialize the booking repository with the Booking model."""
        super().__init__(Booking)
    
    def get_by_booking_id(self, db: Session, booking_id: str) -> Optional[Booking]:
        """
        Retrieve a booking by its booking ID with user and property relationships loaded.
        
        Args:
            db: Database session
            booking_id: Unique booking identifier
            
        Returns:
            Booking instance with user and property loaded if found, None otherwise
        """
        from sqlalchemy.orm import joinedload
        return (
            db.query(Booking)
            .options(joinedload(Booking.user), joinedload(Booking.property))
            .filter(Booking.booking_id == booking_id)
            .first()
        )
    
    def get_user_bookings(
        self, 
        db: Session, 
        user_id: str,
        limit: Optional[int] = None
    ) -> List[Booking]:
        """
        Retrieve all bookings for a specific user.
        
        Args:
            db: Database session
            user_id: User's unique identifier
            limit: Optional maximum number of bookings to return
            
        Returns:
            List of booking instances ordered by creation date (newest first)
        """
        query = (
            db.query(Booking)
            .filter(Booking.user_id == user_id)
            .order_by(Booking.created_at.desc())
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def check_availability(
        self,
        db: Session,
        property_id: str,
        booking_date: datetime,
        shift_type: str
    ) -> bool:
        """
        Check if a property is available for booking on a specific date and shift.
        
        Handles complex shift conflicts:
        - Full Day: Conflicts with Day, Night, Full Day on same date, and Full Night on same/previous date
        - Full Night: Conflicts with Night on same date, Day on next date, Full Day on same/next date, Full Night on same date
        - Day: Conflicts with Day, Full Day on same date, Full Night on previous date
        - Night: Conflicts with Night, Full Day on same date, Full Night on same date
        
        Args:
            db: Database session
            property_id: Property's unique identifier
            booking_date: Date to check availability for
            shift_type: Shift type ("Day", "Night", "Full Day", or "Full Night")
            
        Returns:
            True if property is available, False if already booked
        """
        from datetime import timedelta
        
        # Define conflict rules for each shift type
        if shift_type == "Full Day":
            # Full Day = Day + Night on same date
            # Conflicts with: Day, Night, Full Day on same date
            # Also conflicts with: Full Night on same date or previous date
            next_date = booking_date + timedelta(days=1)
            
            conflicting_bookings = db.query(Booking).filter(
                and_(
                    Booking.property_id == property_id,
                    Booking.status.in_(["Pending", "Confirmed"]),
                    and_(
                        Booking.booking_date == booking_date,
                        Booking.shift_type.in_(["Day", "Night", "Full Day", "Full Night"])
                    )
                )
            ).first()
            
            return conflicting_bookings is None
            
        elif shift_type == "Full Night":
            # Full Night = Night on booking_date + Day on next_date
            # Conflicts with:
            #   - Night, Full Day, Full Night on booking_date
            #   - Day, Full Day on next_date
            #   - Full Night on previous date (which extends to booking_date's Day)
            next_date = booking_date + timedelta(days=1)
            prev_date = booking_date - timedelta(days=1)
            
            # Check booking_date for Night, Full Day, Full Night
            conflict_same_date = db.query(Booking).filter(
                and_(
                    Booking.property_id == property_id,
                    Booking.booking_date == booking_date,
                    Booking.shift_type.in_(["Night", "Full Day", "Full Night"]),
                    Booking.status.in_(["Pending", "Confirmed"])
                )
            ).first()
            
            if conflict_same_date:
                return False
            
            # Check next_date for Day, Full Day, Full Night
            conflict_next_date = db.query(Booking).filter(
                and_(
                    Booking.property_id == property_id,
                    Booking.booking_date == next_date,
                    Booking.shift_type.in_(["Day", "Full Day", "Full Night"]),
                    Booking.status.in_(["Pending", "Confirmed"])
                )
            ).first()
            
            return conflict_next_date is None
            
        elif shift_type == "Day":
            # Day shift conflicts with:
            #   - Day, Full Day on same date
            #   - Full Night on previous date (which extends to this Day)
            prev_date = booking_date - timedelta(days=1)
            
            # Check same date
            conflict_same_date = db.query(Booking).filter(
                and_(
                    Booking.property_id == property_id,
                    Booking.booking_date == booking_date,
                    Booking.shift_type.in_(["Day", "Full Day"]),
                    Booking.status.in_(["Pending", "Confirmed"])
                )
            ).first()
            
            if conflict_same_date:
                return False
            
            # Check previous date for Full Night
            conflict_prev_night = db.query(Booking).filter(
                and_(
                    Booking.property_id == property_id,
                    Booking.booking_date == prev_date,
                    Booking.shift_type == "Full Night",
                    Booking.status.in_(["Pending", "Confirmed"])
                )
            ).first()
            
            return conflict_prev_night is None
            
        elif shift_type == "Night":
            # Night shift conflicts with:
            #   - Night, Full Day, Full Night on same date
            conflicting_bookings = db.query(Booking).filter(
                and_(
                    Booking.property_id == property_id,
                    Booking.booking_date == booking_date,
                    Booking.shift_type.in_(["Night", "Full Day", "Full Night"]),
                    Booking.status.in_(["Pending", "Confirmed"])
                )
            ).first()
            
            return conflicting_bookings is None
        
        # Fallback for unknown shift types
        return False
    
    def update_status(
        self,
        db: Session,
        booking_id: str,
        status: str
    ) -> Optional[Booking]:
        """
        Update the status of a booking.
        
        Args:
            db: Database session
            booking_id: Unique booking identifier
            status: New status value (e.g., "Pending", "Confirmed", "Cancelled", "Expired")
            
        Returns:
            Updated booking instance if found, None otherwise
        """
        booking = self.get_by_booking_id(db, booking_id)
        
        if booking:
            booking.status = status
            booking.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(booking)
        
        return booking
    
    def get_pending_bookings(
        self,
        db: Session,
        older_than_minutes: Optional[int] = None
    ) -> List[Booking]:
        """
        Retrieve all bookings with 'Pending' status.
        
        Optionally filter for bookings older than a specified number of minutes,
        useful for finding expired pending bookings.
        
        Args:
            db: Database session
            older_than_minutes: Optional filter to get bookings created more than
                              this many minutes ago
            
        Returns:
            List of pending booking instances
        """
        query = db.query(Booking).filter(Booking.status == "Pending")
        
        if older_than_minutes is not None:
            cutoff_time = datetime.utcnow() - timedelta(minutes=older_than_minutes)
            query = query.filter(Booking.created_at < cutoff_time)
        
        return query.all()
    
    def get_expired_bookings(
        self,
        db: Session,
        expiration_minutes: int = 15
    ) -> List[Booking]:
        """
        Retrieve pending bookings that have expired.
        
        A booking is considered expired if it has 'Pending' status and was
        created more than the specified number of minutes ago.
        
        Args:
            db: Database session
            expiration_minutes: Number of minutes after which a pending booking
                              is considered expired (default: 15)
            
        Returns:
            List of expired pending booking instances
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=expiration_minutes)
        
        expired_bookings = db.query(Booking).filter(
            and_(
                Booking.status == "Pending",
                Booking.created_at < cutoff_time
            )
        ).all()
        
        return expired_bookings
    
    def get_payment_screenshot_url(
        self,
        db: Session,
        booking_id: str
    ) -> Optional[str]:
        """
        Get the payment screenshot URL for a booking.
        
        Args:
            db: Database session
            booking_id: Unique booking identifier
            
        Returns:
            Payment screenshot URL if exists, None otherwise
        """
        booking = self.get_by_booking_id(db, booking_id)
        return booking.payment_screenshot_url if booking else None
    
    def update_payment_screenshot_url(
        self,
        db: Session,
        booking_id: str,
        screenshot_url: str
    ) -> Optional[Booking]:
        """
        Update the payment screenshot URL for a booking.
        
        Args:
            db: Database session
            booking_id: Unique booking identifier
            screenshot_url: Cloudinary URL of the payment screenshot
            
        Returns:
            Updated booking instance if found, None otherwise
        """
        booking = self.get_by_booking_id(db, booking_id)
        
        if booking:
            booking.payment_screenshot_url = screenshot_url
            booking.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(booking)
        
        return booking
