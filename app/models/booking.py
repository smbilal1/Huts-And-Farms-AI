from sqlalchemy import Column, DateTime, ForeignKey, Text, Enum, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    booking_id = Column(Text, primary_key=True)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)  # Foreign key to users
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.property_id"), nullable=False)
    booking_date = Column(DateTime, nullable=False)
    shift_type = Column(Enum("Day", "Night", "Full Day", "Full Night", name="shift_type_enum"), nullable=False)
    total_cost = Column(Numeric(10, 2), nullable=False)
    booking_source = Column(Enum("Website", "Bot", "Third-Party", name="booking_source_enum"), nullable=False)
    status = Column(Enum("Pending", "Waiting", "Confirmed", "Cancelled", "Completed", "Expired", name="booking_status_enum"), default="Pending")
    booked_at = Column(DateTime)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    user = relationship("User", backref="bookings")
    property = relationship("Property", backref="Booking")
