"""
Input validation utilities.

This module contains pure functions for validating various types of input data.
"""

import re
from datetime import datetime
from typing import Optional, Tuple


def validate_cnic(cnic: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Pakistani CNIC (Computerized National Identity Card) number.
    
    CNIC format: XXXXX-XXXXXXX-X (13 digits)
    
    Args:
        cnic: CNIC number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> validate_cnic("12345-1234567-1")
        (True, None)
        >>> validate_cnic("12345")
        (False, "CNIC must be 13 digits")
    """
    if not cnic:
        return False, "CNIC is required"
    
    # Remove any formatting (dashes, spaces)
    cnic_digits = re.sub(r'[^\d]', '', cnic)
    
    # Check length
    if len(cnic_digits) != 13:
        return False, "CNIC must be 13 digits"
    
    # Check if all characters are digits
    if not cnic_digits.isdigit():
        return False, "CNIC must contain only digits"
    
    return True, None


def validate_phone_number(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Pakistani phone number.
    
    Accepts formats:
    - 03XXXXXXXXX (11 digits)
    - 923XXXXXXXXX (12 digits with country code)
    - +923XXXXXXXXX (with + prefix)
    
    Args:
        phone: Phone number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> validate_phone_number("03001234567")
        (True, None)
        >>> validate_phone_number("12345")
        (False, "Invalid phone number format")
    """
    if not phone:
        return False, "Phone number is required"
    
    # Remove any formatting
    phone_digits = re.sub(r'[^\d]', '', phone)
    
    # Check Pakistani mobile number patterns
    if len(phone_digits) == 11 and phone_digits.startswith('03'):
        return True, None
    elif len(phone_digits) == 12 and phone_digits.startswith('923'):
        return True, None
    else:
        return False, "Invalid phone number format. Use 03XXXXXXXXX or 923XXXXXXXXX"


def validate_date(date_str: str, date_format: str = "%Y-%m-%d") -> Tuple[bool, Optional[str]]:
    """
    Validate date string format.
    
    Args:
        date_str: Date string to validate
        date_format: Expected date format (default: "%Y-%m-%d")
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> validate_date("2024-01-15")
        (True, None)
        >>> validate_date("invalid")
        (False, "Invalid date format. Expected YYYY-MM-DD")
    """
    if not date_str:
        return False, "Date is required"
    
    try:
        datetime.strptime(date_str, date_format)
        return True, None
    except ValueError:
        return False, f"Invalid date format. Expected {date_format}"


def validate_booking_id(booking_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate booking ID format.
    
    Expected format: NAME-YYYY-MM-DD-SHIFT
    Example: JohnDoe-2024-01-15-Day
    
    Args:
        booking_id: Booking ID to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> validate_booking_id("JohnDoe-2024-01-15-Day")
        (True, None)
        >>> validate_booking_id("invalid")
        (False, "Invalid booking ID format")
    """
    if not booking_id:
        return False, "Booking ID is required"
    
    # Expected format: NAME-YYYY-MM-DD-SHIFT
    pattern = r'^.+-\d{4}-\d{2}-\d{2}-(Day|Night|Full Day)$'
    
    if re.match(pattern, booking_id):
        return True, None
    else:
        return False, "Invalid booking ID format. Expected: NAME-YYYY-MM-DD-SHIFT"


def validate_shift_type(shift_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate shift type.
    
    Valid shift types: Day, Night, Full Day
    
    Args:
        shift_type: Shift type to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> validate_shift_type("Day")
        (True, None)
        >>> validate_shift_type("Invalid")
        (False, "Invalid shift type. Must be Day, Night, or Full Day")
    """
    if not shift_type:
        return False, "Shift type is required"
    
    valid_shifts = ["Day", "Night", "Full Day"]
    
    if shift_type in valid_shifts:
        return True, None
    else:
        return False, f"Invalid shift type. Must be one of: {', '.join(valid_shifts)}"


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> validate_email("user@example.com")
        (True, None)
        >>> validate_email("invalid")
        (False, "Invalid email format")
    """
    if not email:
        return False, "Email is required"
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(pattern, email):
        return True, None
    else:
        return False, "Invalid email format"


def validate_amount(amount: float, min_amount: float = 0) -> Tuple[bool, Optional[str]]:
    """
    Validate monetary amount.
    
    Args:
        amount: Amount to validate
        min_amount: Minimum allowed amount (default: 0)
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> validate_amount(1000)
        (True, None)
        >>> validate_amount(-100)
        (False, "Amount must be greater than or equal to 0")
    """
    if amount is None:
        return False, "Amount is required"
    
    if amount < min_amount:
        return False, f"Amount must be greater than or equal to {min_amount}"
    
    return True, None
