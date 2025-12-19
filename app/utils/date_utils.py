"""
Date parsing and formatting utilities.

This module contains pure functions for working with dates.
"""

from datetime import datetime, date, timedelta
from typing import Optional, Tuple
import calendar


def parse_date(date_str: str, date_format: str = "%Y-%m-%d") -> Optional[datetime]:
    """
    Parse date string to datetime object.
    
    Args:
        date_str: Date string to parse
        date_format: Expected date format (default: "%Y-%m-%d")
        
    Returns:
        Datetime object or None if parsing fails
        
    Example:
        >>> parse_date("2024-01-15")
        datetime.datetime(2024, 1, 15, 0, 0)
    """
    if not date_str:
        return None
    
    try:
        return datetime.strptime(date_str, date_format)
    except ValueError:
        return None


def format_date(dt: datetime, date_format: str = "%Y-%m-%d") -> str:
    """
    Format datetime object to string.
    
    Args:
        dt: Datetime object to format
        date_format: Output date format (default: "%Y-%m-%d")
        
    Returns:
        Formatted date string
        
    Example:
        >>> format_date(datetime(2024, 1, 15))
        '2024-01-15'
    """
    if not dt:
        return ""
    
    return dt.strftime(date_format)


def get_day_of_week(dt: datetime) -> str:
    """
    Get day of week name from datetime.
    
    Args:
        dt: Datetime object
        
    Returns:
        Day name (e.g., "Monday", "Tuesday")
        
    Example:
        >>> get_day_of_week(datetime(2024, 1, 15))
        'Monday'
    """
    if not dt:
        return ""
    
    return calendar.day_name[dt.weekday()]


def validate_date_range(
    start_date: datetime,
    end_date: datetime,
    min_days: int = 0,
    max_days: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate date range.
    
    Args:
        start_date: Start date
        end_date: End date
        min_days: Minimum days between dates (default: 0)
        max_days: Maximum days between dates (optional)
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> validate_date_range(datetime(2024, 1, 1), datetime(2024, 1, 15))
        (True, None)
    """
    if not start_date or not end_date:
        return False, "Both start and end dates are required"
    
    if end_date < start_date:
        return False, "End date must be after start date"
    
    days_diff = (end_date - start_date).days
    
    if days_diff < min_days:
        return False, f"Date range must be at least {min_days} days"
    
    if max_days and days_diff > max_days:
        return False, f"Date range cannot exceed {max_days} days"
    
    return True, None


def is_past_date(dt: datetime) -> bool:
    """
    Check if date is in the past.
    
    Args:
        dt: Datetime object to check
        
    Returns:
        True if date is in the past, False otherwise
        
    Example:
        >>> is_past_date(datetime(2020, 1, 1))
        True
    """
    if not dt:
        return False
    
    return dt.date() < date.today()


def is_future_date(dt: datetime) -> bool:
    """
    Check if date is in the future.
    
    Args:
        dt: Datetime object to check
        
    Returns:
        True if date is in the future, False otherwise
        
    Example:
        >>> is_future_date(datetime(2030, 1, 1))
        True
    """
    if not dt:
        return False
    
    return dt.date() > date.today()


def add_days(dt: datetime, days: int) -> datetime:
    """
    Add days to a datetime.
    
    Args:
        dt: Datetime object
        days: Number of days to add (can be negative)
        
    Returns:
        New datetime object
        
    Example:
        >>> add_days(datetime(2024, 1, 15), 7)
        datetime.datetime(2024, 1, 22, 0, 0)
    """
    if not dt:
        return None
    
    return dt + timedelta(days=days)


def get_date_range(start_date: datetime, end_date: datetime) -> list[datetime]:
    """
    Get list of dates between start and end date (inclusive).
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        List of datetime objects
        
    Example:
        >>> get_date_range(datetime(2024, 1, 1), datetime(2024, 1, 3))
        [datetime(2024, 1, 1), datetime(2024, 1, 2), datetime(2024, 1, 3)]
    """
    if not start_date or not end_date:
        return []
    
    if end_date < start_date:
        return []
    
    dates = []
    current_date = start_date
    
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    
    return dates


def format_relative_date(dt: datetime) -> str:
    """
    Format date as relative string (e.g., "Today", "Tomorrow", "Yesterday").
    
    Args:
        dt: Datetime object
        
    Returns:
        Relative date string
        
    Example:
        >>> format_relative_date(datetime.now())
        'Today'
    """
    if not dt:
        return ""
    
    today = date.today()
    dt_date = dt.date()
    
    if dt_date == today:
        return "Today"
    elif dt_date == today + timedelta(days=1):
        return "Tomorrow"
    elif dt_date == today - timedelta(days=1):
        return "Yesterday"
    else:
        return format_date(dt, "%B %d, %Y")


def get_weekday_name(weekday: int) -> str:
    """
    Get weekday name from weekday number.
    
    Args:
        weekday: Weekday number (0=Monday, 6=Sunday)
        
    Returns:
        Weekday name
        
    Example:
        >>> get_weekday_name(0)
        'Monday'
    """
    if weekday < 0 or weekday > 6:
        return ""
    
    return calendar.day_name[weekday]
