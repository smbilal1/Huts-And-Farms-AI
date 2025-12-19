"""
Property service for business logic related to properties.

This module provides business logic for property operations including
searching properties, retrieving property details, and checking availability.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.repositories.property_repository import PropertyRepository
from app.repositories.booking_repository import BookingRepository
from app.core.exceptions import PropertyException

logger = logging.getLogger(__name__)


class PropertyService:
    """
    Service class for property-related business logic.
    
    This service orchestrates property operations by coordinating between
    the property repository and booking repository to provide comprehensive
    property information and availability checks.
    """
    
    def __init__(
        self,
        property_repo: PropertyRepository,
        booking_repo: BookingRepository
    ):
        """
        Initialize the property service with required repositories.
        
        Args:
            property_repo: Repository for property data access
            booking_repo: Repository for booking data access (for availability checks)
        """
        self.property_repo = property_repo
        self.booking_repo = booking_repo
    
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
    ) -> Dict[str, Any]:
        """
        Search for properties based on filters and availability.
        
        This method applies business logic for property search including
        validation, filtering, and formatting results for client consumption.
        
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
            Dictionary with 'properties' list and metadata
        """
        try:
            # Validate property type
            valid_types = ['hut', 'farm']
            if property_type.lower() not in valid_types:
                raise PropertyException(
                    message=f"Invalid property type. Must be one of: {', '.join(valid_types)}",
                    code="INVALID_PROPERTY_TYPE"
                )
            
            # Validate shift type
            valid_shifts = ['Day', 'Night', 'Full Day', 'Full Night']
            if shift_type not in valid_shifts:
                raise PropertyException(
                    message=f"Invalid shift type. Must be one of: {', '.join(valid_shifts)}",
                    code="INVALID_SHIFT_TYPE"
                )
            
            # Validate date is not in the past
            if booking_date.date() < datetime.now().date():
                raise PropertyException(
                    message="Booking date cannot be in the past",
                    code="INVALID_BOOKING_DATE"
                )
            
            # Search properties using repository
            properties = self.property_repo.search_properties(
                db=db,
                property_type=property_type.lower(),
                booking_date=booking_date,
                shift_type=shift_type,
                city=city,
                country=country,
                min_price=min_price,
                max_price=max_price,
                max_occupancy=max_occupancy,
                include_booked=include_booked
            )
            
            logger.info(f"Property search completed: found {len(properties)} properties")
            
            # Format response
            return {
                "properties": properties,
                "count": len(properties),
                "filters": {
                    "property_type": property_type,
                    "city": city,
                    "country": country,
                    "booking_date": booking_date.strftime("%Y-%m-%d"),
                    "shift_type": shift_type
                }
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error searching properties: {e}", exc_info=True)
            raise PropertyException(
                message="Database error occurred while searching properties",
                code="PROPERTY_SEARCH_DB_ERROR"
            )
        except PropertyException:
            # Re-raise PropertyException without wrapping
            raise
        except Exception as e:
            logger.error(f"Error searching properties: {e}", exc_info=True)
            raise PropertyException(
                message="Failed to search properties. Please try again.",
                code="PROPERTY_SEARCH_FAILED"
            )
    
    def get_property_details(
        self,
        db: Session,
        property_id: str,
        include_media: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive details for a specific property.
        
        This method retrieves all property information including basic details,
        pricing, amenities, and optionally media (images and videos).
        
        Args:
            db: Database session
            property_id: Property UUID
            include_media: If True, include images and videos (default: True)
            
        Returns:
            Dictionary containing property details or error message
        """
        try:
            # Get property details from repository
            property_details = self.property_repo.get_property_details(db, property_id)
            
            if not property_details:
                raise PropertyException(
                    message="Property not found",
                    code="PROPERTY_NOT_FOUND"
                )
            
            # Add media if requested
            if include_media:
                property_details["images"] = self.get_property_images(db, property_id)
                property_details["videos"] = self.get_property_videos(db, property_id)
            
            logger.info(f"Property details retrieved: {property_id}")
            
            return property_details
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting property details: {e}", exc_info=True)
            raise PropertyException(
                message="Database error occurred while retrieving property details",
                code="PROPERTY_DETAILS_DB_ERROR"
            )
        except PropertyException:
            # Re-raise PropertyException without wrapping
            raise
        except Exception as e:
            logger.error(f"Error getting property details: {e}", exc_info=True)
            raise PropertyException(
                message="Failed to retrieve property details. Please try again.",
                code="PROPERTY_DETAILS_FAILED"
            )
    
    def get_property_images(
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
            List of image URLs (empty list if none found)
        """
        try:
            return self.property_repo.get_images(db, property_id)
        except SQLAlchemyError as e:
            logger.error(f"Database error getting property images: {e}", exc_info=True)
            raise PropertyException(
                message="Database error occurred while retrieving property images",
                code="PROPERTY_IMAGES_DB_ERROR"
            )
        except Exception as e:
            logger.error(f"Error getting property images: {e}", exc_info=True)
            raise PropertyException(
                message="Failed to retrieve property images",
                code="PROPERTY_IMAGES_FAILED"
            )
    
    def get_property_videos(
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
            List of video URLs (empty list if none found)
        """
        try:
            return self.property_repo.get_videos(db, property_id)
        except SQLAlchemyError as e:
            logger.error(f"Database error getting property videos: {e}", exc_info=True)
            raise PropertyException(
                message="Database error occurred while retrieving property videos",
                code="PROPERTY_VIDEOS_DB_ERROR"
            )
        except Exception as e:
            logger.error(f"Error getting property videos: {e}", exc_info=True)
            raise PropertyException(
                message="Failed to retrieve property videos",
                code="PROPERTY_VIDEOS_FAILED"
            )
    
    def check_availability(
        self,
        db: Session,
        property_id: str,
        booking_date: datetime,
        shift_type: str
    ) -> Dict[str, Any]:
        """
        Check if a property is available for booking.
        
        This method validates the property exists, checks availability,
        and returns pricing information if available.
        
        Args:
            db: Database session
            property_id: Property UUID
            booking_date: Date to check availability for
            shift_type: Shift type ('Day', 'Night', 'Full Day', 'Full Night')
            
        Returns:
            Dictionary with availability status, pricing, and property info
        """
        try:
            # Validate property exists
            property_obj = self.property_repo.get_by_id(db, property_id)
            if not property_obj:
                raise PropertyException(
                    message="Property not found",
                    code="PROPERTY_NOT_FOUND"
                )
            
            # Validate shift type
            valid_shifts = ['Day', 'Night', 'Full Day', 'Full Night']
            if shift_type not in valid_shifts:
                raise PropertyException(
                    message=f"Invalid shift type. Must be one of: {', '.join(valid_shifts)}",
                    code="INVALID_SHIFT_TYPE"
                )
            
            # Validate date is not in the past
            if booking_date.date() < datetime.now().date():
                raise PropertyException(
                    message="Booking date cannot be in the past",
                    code="INVALID_BOOKING_DATE"
                )
            
            # Check availability using booking repository
            is_available = self.booking_repo.check_availability(
                db=db,
                property_id=property_id,
                booking_date=booking_date,
                shift_type=shift_type
            )
            
            # Get pricing information
            pricing = self.property_repo.get_pricing(
                db=db,
                property_id=property_id,
                booking_date=booking_date,
                shift_type=shift_type
            )
            
            result = {
                "available": is_available,
                "property_id": property_id,
                "property_name": property_obj.name,
                "booking_date": booking_date.strftime("%Y-%m-%d"),
                "shift_type": shift_type
            }
            
            if pricing:
                result["price"] = float(pricing.price)
                result["day_of_week"] = pricing.day_of_week
            else:
                result["price"] = None
                result["error"] = "Pricing not available for this date and shift"
            
            if not is_available:
                result["message"] = "Property is already booked for this date and shift"
            
            logger.info(f"Availability checked for property {property_id}: {is_available}")
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Database error checking availability: {e}", exc_info=True)
            raise PropertyException(
                message="Database error occurred while checking availability",
                code="AVAILABILITY_CHECK_DB_ERROR"
            )
        except PropertyException:
            # Re-raise PropertyException without wrapping
            raise
        except Exception as e:
            logger.error(f"Error checking availability: {e}", exc_info=True)
            raise PropertyException(
                message="Failed to check availability. Please try again.",
                code="AVAILABILITY_CHECK_FAILED"
            )
    
    def get_property_by_name(
        self,
        db: Session,
        property_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get property by name (case-insensitive).
        
        This is a convenience method for looking up properties by name,
        useful for chatbot interactions where users refer to properties by name.
        
        Args:
            db: Database session
            property_name: Property name to search for
            
        Returns:
            Dictionary with property_id and name if found, None otherwise
        """
        try:
            property_obj = self.property_repo.get_by_name(db, property_name)
            
            if not property_obj:
                return None
            
            return {
                "property_id": str(property_obj.property_id),
                "name": property_obj.name,
                "type": property_obj.type,
                "city": property_obj.city
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting property by name: {e}", exc_info=True)
            raise PropertyException(
                message="Database error occurred while searching for property",
                code="PROPERTY_BY_NAME_DB_ERROR"
            )
        except Exception as e:
            logger.error(f"Error getting property by name: {e}", exc_info=True)
            raise PropertyException(
                message="Failed to search for property by name",
                code="PROPERTY_BY_NAME_FAILED"
            )
