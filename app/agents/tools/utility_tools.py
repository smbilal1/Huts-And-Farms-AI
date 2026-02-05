"""
Utility tools for the booking agent
"""
from langchain.tools import tool
from typing import Dict, Optional
from datetime import datetime
import calendar


@tool("check_message_relevance")
def check_message_relevance(user_message: str) -> dict:
    """
    CALL: always check if user message relates to bookings
    NO CALL: never for internal system messages

    REQ:
    • user_message (string)

    RETURNS:
    ok {is_relevant, category, optional redirect_message}
    err {rare - not applicable}
    """
    # Simple implementation - can be enhanced with NLP
    booking_keywords = [
        "book", "booking", "reserve", "rent", "farmhouse", "hut", 
        "property", "available", "price", "cost", "date", "shift"
    ]
    
    greeting_keywords = ["hello", "hi", "salam", "assalam"]
    
    message_lower = user_message.lower()
    
    # Check for greetings
    if any(keyword in message_lower for keyword in greeting_keywords):
        return {
            "is_relevant": True,
            "category": "greeting",
            "redirect_message": None
        }
    
    # Check for booking-related keywords
    if any(keyword in message_lower for keyword in booking_keywords):
        return {
            "is_relevant": True,
            "category": "booking",
            "redirect_message": None
        }
    
    # Default to relevant (let the agent handle it)
    return {
        "is_relevant": True,
        "category": "booking",
        "redirect_message": None
    }

@tool("send_booking_intro")
def send_booking_intro() -> str:
    """
    CALL: greeting new user or explaining booking process
    NO CALL: specific booking queries, media requests

    REQ: none

    RETURNS:
    ok {formatted WhatsApp intro message}
    """

    message = """
    Hello! I’m HutBuddy AI, your booking assistant.

    I can help you with:
    ‣   🏡 Booking huts and farmhouses
    ‣   📅 Checking availability
    ‣   💸 Guiding you through the booking and payment process
    
    If you share the following details with me, I’ll show you the best available farmhouses/huts:

       ‣ *Farmhouse / Hut*
       ‣ *Date*
       ‣ *Shift Type (Day / Night / Full Day / Full Night)*
            - Day   -> 8 am to 6 pm
            - Night -> 8 pm to 6 am
            - Full Day   -> 8 am to 6 am next day
            - Full Night -> 8 pm to 6 pm next day
       ‣ *Number of People*
       ‣ *Price Range* (optional)

    """
    return message

@tool("check_booking_date")
def check_booking_date(day: int, month: int = None, year: int = None) -> dict:
    """
    CALL: validate a user-provided date
    NO CALL: unrelated messages

    REQ:
    • day (int)
    • month (optional, defaults to current)
    • year (optional, defaults to current)

    RETURNS:
    ok {is_valid: True, formatted date info}
    err {is_valid: False, message explaining invalidity}
    """
    # Get current date information
    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    current_day = current_date.day
    
    # Calculate next month and year
    if current_month == 12:
        next_month = 1
        next_year = current_year + 1
    else:
        next_month = current_month + 1
        next_year = current_year
    
    # Get month names
    current_month_name = calendar.month_name[current_month]
    next_month_name = calendar.month_name[next_month]
    
    # Set default values if not provided
    if month is None:
        month = current_month
    if year is None:
        year = current_year
    
    # Validate month and year
    if year < current_year or (year == current_year and month < current_month):
        return {
            "is_valid": False,
            "message": f"❌ Cannot book for past dates. Please select {current_month_name} or {next_month_name}.",
            "date_info": None
        }
    
    # Only allow current month and next month
    if year > next_year or (year == next_year and month > next_month):
        return {
            "is_valid": False,
            "message": f"❌ Booking only available for {current_month_name} and {next_month_name}.",
            "date_info": None
        }
    
    # Validate day
    try:
        booking_date = datetime(year, month, day)
    except ValueError:
        return {
            "is_valid": False,
            "message": f"❌ Invalid date. Please check the day ({day}) for {calendar.month_name[month]}.",
            "date_info": None
        }
    
    # Check if date is in the past
    if booking_date.date() < current_date.date():
        return {
            "is_valid": False,
            "message": f"❌ Cannot book for past dates. Please select a future date.",
            "date_info": None
        }
    
    # Date is valid
    day_name = booking_date.strftime("%A")
    formatted_date = booking_date.strftime("%d %B %Y")
    
    return {
        "is_valid": True,
        "message": f"✅ Date is valid: {formatted_date} ({day_name})",
        "date_info": {
            "date": booking_date.strftime("%Y-%m-%d"),
            "day_name": day_name,
            "formatted": formatted_date
        }
    }
