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
        
        A property is considered unavailable if there's an existing booking
        with status 'Pending' or 'Confirmed' for the same date and shift.
        
        Args:
            db: Database session
            property_id: Property's unique identifier
            booking_date: Date to check availability for
            shift_type: Shift type ("Day", "Night", "Full Day", or "Full Night")
            
        Returns:
            True if property is available, False if already booked
        """
        existing_booking = db.query(Booking).filter(
            and_(
                Booking.property_id == property_id,
                Booking.booking_date == booking_date,
                Booking.shift_type == shift_type,
                Booking.status.in_(["Pending", "Confirmed"])
            )
        ).first()
        
        return existing_booking is None
    
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
