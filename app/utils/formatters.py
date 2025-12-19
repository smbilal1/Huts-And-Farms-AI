"""
Message and text formatting utilities.

This module contains pure functions for formatting messages,
particularly for WhatsApp markdown formatting.
"""

import re
from typing import Optional, List


def formatting(text: str) -> str:
    """
    Format text for WhatsApp markdown.
    
    Converts markdown-style formatting to WhatsApp formatting and removes HTML tags:
    - **text** -> *text* (bold)
    - Removes HTML tags
    
    This is the main formatting function used throughout the application.
    
    Args:
        text: The text to format
        
    Returns:
        Formatted text with WhatsApp markdown and HTML tags removed
        
    Example:
        >>> formatting("Hello **world**!")
        'Hello *world*!'
        >>> formatting("Hello <b>world</b>!")
        'Hello world!'
    """
    if not text:
        return text
    
    # Convert Markdown bold to WhatsApp bold
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)
    
    # Remove HTML tags
    text = re.sub(r"<[^>]*>", "", text)
    
    return text


def format_bold(text: str) -> str:
    """
    Format text as bold for WhatsApp.
    
    Args:
        text: The text to make bold
        
    Returns:
        Text wrapped in WhatsApp bold markers
        
    Example:
        >>> format_bold("Important")
        '*Important*'
    """
    if not text:
        return text
    return f"*{text}*"


def format_italic(text: str) -> str:
    """
    Format text as italic for WhatsApp.
    
    Args:
        text: The text to make italic
        
    Returns:
        Text wrapped in WhatsApp italic markers
        
    Example:
        >>> format_italic("Note")
        '_Note_'
    """
    if not text:
        return text
    return f"_{text}_"


def format_strikethrough(text: str) -> str:
    """
    Format text as strikethrough for WhatsApp.
    
    Args:
        text: The text to strikethrough
        
    Returns:
        Text wrapped in WhatsApp strikethrough markers
        
    Example:
        >>> format_strikethrough("Cancelled")
        '~Cancelled~'
    """
    if not text:
        return text
    return f"~{text}~"


def format_monospace(text: str) -> str:
    """
    Format text as monospace for WhatsApp.
    
    Args:
        text: The text to format as monospace
        
    Returns:
        Text wrapped in WhatsApp monospace markers
        
    Example:
        >>> format_monospace("CODE123")
        '```CODE123```'
    """
    if not text:
        return text
    return f"```{text}```"


def clean_message(text: str) -> str:
    """
    Clean message text by removing extra whitespace and newlines.
    
    Args:
        text: The text to clean
        
    Returns:
        Cleaned text
        
    Example:
        >>> clean_message("Hello\\n\\n\\nworld")
        'Hello\\n\\nworld'
    """
    if not text:
        return text
    
    # Replace multiple newlines with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove trailing/leading whitespace
    text = text.strip()
    
    return text


def remove_html_tags(text: str) -> str:
    """
    Remove all HTML tags from text.
    
    Args:
        text: The text to clean
        
    Returns:
        Text with HTML tags removed
        
    Example:
        >>> remove_html_tags("Hello <b>world</b>!")
        'Hello world!'
    """
    if not text:
        return text
    
    return re.sub(r"<[^>]*>", "", text)


def sanitize_whatsapp_message(text: str) -> str:
    """
    Sanitize text for WhatsApp by removing problematic characters.
    
    Args:
        text: The text to sanitize
        
    Returns:
        Sanitized text safe for WhatsApp
        
    Example:
        >>> sanitize_whatsapp_message("Hello\\x00world")
        'Helloworld'
    """
    if not text:
        return text
    
    # Remove null bytes and other control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    return text


def format_whatsapp_list(items: List[str], numbered: bool = False) -> str:
    """
    Format a list for WhatsApp display.
    
    Args:
        items: List of items to format
        numbered: If True, create numbered list; otherwise bullet points
        
    Returns:
        Formatted list string
        
    Example:
        >>> format_whatsapp_list(["Item 1", "Item 2"], numbered=True)
        '1. Item 1\\n2. Item 2'
    """
    if not items:
        return ""
    
    if numbered:
        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
    else:
        return "\n".join(f"• {item}" for item in items)


def format_whatsapp_section(title: str, content: str, use_bold: bool = True) -> str:
    """
    Format a section with title and content for WhatsApp.
    
    Args:
        title: Section title
        content: Section content
        use_bold: Whether to make title bold (default: True)
        
    Returns:
        Formatted section
        
    Example:
        >>> format_whatsapp_section("Details", "Some information")
        '*Details*\\nSome information'
    """
    if not title:
        return content
    
    formatted_title = format_bold(title) if use_bold else title
    
    if not content:
        return formatted_title
    
    return f"{formatted_title}\n{content}"


def format_key_value(key: str, value: str, separator: str = ": ") -> str:
    """
    Format a key-value pair for display.
    
    Args:
        key: The key/label
        value: The value
        separator: Separator between key and value (default: ": ")
        
    Returns:
        Formatted key-value string
        
    Example:
        >>> format_key_value("Name", "John Doe")
        'Name: John Doe'
    """
    if not key:
        return value
    if not value:
        return key
    
    return f"{key}{separator}{value}"


def format_currency(amount: float, currency: str = "PKR") -> str:
    """
    Format currency amount for display.
    
    Args:
        amount: The amount to format
        currency: Currency code (default: PKR)
        
    Returns:
        Formatted currency string
        
    Example:
        >>> format_currency(5000)
        'PKR 5,000'
    """
    formatted_amount = f"{amount:,.0f}"
    return f"{currency} {formatted_amount}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: The text to truncate
        max_length: Maximum length (default: 100)
        suffix: Suffix to add if truncated (default: "...")
        
    Returns:
        Truncated text
        
    Example:
        >>> truncate_text("This is a very long text", max_length=10)
        'This is...'
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_phone_number(phone: str) -> str:
    """
    Format phone number for display.
    
    Args:
        phone: Phone number to format
        
    Returns:
        Formatted phone number
        
    Example:
        >>> format_phone_number("923001234567")
        '+92 300 1234567'
    """
    if not phone:
        return phone
    
    # Remove any existing formatting
    phone = re.sub(r'[^\d]', '', phone)
    
    # Add country code if not present
    if not phone.startswith('92'):
        phone = '92' + phone
    
    # Format as +92 XXX XXXXXXX
    if len(phone) >= 12:
        return f"+{phone[:2]} {phone[2:5]} {phone[5:]}"
    
    return phone
