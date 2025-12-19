"""
Agent tools organized by domain.

This package contains tools for AI agents organized into domain-specific modules:
- booking_tools: Tools for creating and managing bookings
- property_tools: Tools for searching and viewing properties
- payment_tools: Tools for processing payments and verifications
"""

from app.agents.tools.booking_tools import (
    create_booking,
    check_booking_status,
    get_user_bookings,
    get_payment_instructions,
    booking_tools
)

from app.agents.tools.property_tools import (
    list_properties,
    get_property_details,
    get_property_images,
    get_property_videos,
    get_property_id_from_name,
    property_tools
)

from app.agents.tools.payment_tools import (
    process_payment_screenshot,
    process_payment_details,
    confirm_booking_payment,
    reject_booking_payment,
    payment_tools
)

__all__ = [
    # Booking tools
    "create_booking",
    "check_booking_status",
    "get_user_bookings",
    "get_payment_instructions",
    "booking_tools",
    # Property tools
    "list_properties",
    "get_property_details",
    "get_property_images",
    "get_property_videos",
    "get_property_id_from_name",
    "property_tools",
    # Payment tools
    "process_payment_screenshot",
    "process_payment_details",
    "confirm_booking_payment",
    "reject_booking_payment",
    "payment_tools",
]
