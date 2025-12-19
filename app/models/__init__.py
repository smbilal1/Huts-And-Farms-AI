# Import all models for SQLAlchemy registration and backward compatibility
from app.database import Base
from app.models.user import User, Session
from app.models.property import (
    Property,
    PropertyPricing,
    PropertyShiftPricing,
    PropertyImage,
    PropertyVideo,
    PropertyAmenity,
    Owner,
    OwnerProperty
)
from app.models.booking import Booking
from app.models.message import Message

__all__ = [
    "Base",
    "User",
    "Session",
    "Property",
    "PropertyPricing",
    "PropertyShiftPricing",
    "PropertyImage",
    "PropertyVideo",
    "PropertyAmenity",
    "Owner",
    "OwnerProperty",
    "Booking",
    "Message"
]
