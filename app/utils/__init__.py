"""
Utility modules for the booking system.

This package contains utility functions organized by purpose:
- formatters: Message and text formatting utilities
- validators: Input validation utilities
- date_utils: Date parsing and formatting utilities
- media_utils: Media URL extraction and processing utilities
"""

from app.utils.formatters import (
    formatting,
    format_bold,
    format_italic,
    format_strikethrough,
    format_monospace,
    clean_message,
    remove_html_tags,
    sanitize_whatsapp_message,
    format_whatsapp_list,
    format_whatsapp_section,
    format_key_value,
    format_currency,
    truncate_text,
    format_phone_number
)
from app.utils.validators import (
    validate_cnic,
    validate_phone_number,
    validate_date,
    validate_booking_id
)
from app.utils.date_utils import (
    parse_date,
    format_date,
    get_day_of_week,
    validate_date_range,
    is_past_date,
    is_future_date,
    add_days,
    get_date_range,
    format_relative_date,
    get_weekday_name
)
from app.utils.media_utils import (
    extract_media_urls,
    remove_cloudinary_links,
    detect_media_type,
    is_valid_url,
    get_cloudinary_public_id,
    filter_media_urls,
    extract_all_urls
)

__all__ = [
    # Formatters
    "formatting",
    "format_bold",
    "format_italic",
    "format_strikethrough",
    "format_monospace",
    "clean_message",
    "remove_html_tags",
    "sanitize_whatsapp_message",
    "format_whatsapp_list",
    "format_whatsapp_section",
    "format_key_value",
    "format_currency",
    "truncate_text",
    "format_phone_number",
    
    # Validators
    "validate_cnic",
    "validate_phone_number",
    "validate_date",
    "validate_booking_id",
    
    # Date utilities
    "parse_date",
    "format_date",
    "get_day_of_week",
    "validate_date_range",
    "is_past_date",
    "is_future_date",
    "add_days",
    "get_date_range",
    "format_relative_date",
    "get_weekday_name",
    
    # Media utilities
    "extract_media_urls",
    "remove_cloudinary_links",
    "detect_media_type",
    "is_valid_url",
    "get_cloudinary_public_id",
    "filter_media_urls",
    "extract_all_urls",
]
