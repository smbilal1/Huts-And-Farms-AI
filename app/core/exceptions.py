"""
Custom exception classes for the booking system.

This module defines a hierarchy of exceptions used throughout the application
to provide clear error handling and messaging.
"""


class AppException(Exception):
    """
    Base exception for all application-specific errors.
    
    All custom exceptions in the application should inherit from this class.
    
    Attributes:
        message: Human-readable error message
        code: Optional error code for programmatic handling
    """
    
    def __init__(self, message: str, code: str = None):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            code: Optional error code for programmatic handling
        """
        self.message = message
        self.code = code
        super().__init__(self.message)
    
    def __str__(self):
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class BookingException(AppException):
    """
    Exception raised for booking-related errors.
    
    Examples:
        - Booking not found
        - Property already booked
        - Invalid booking date
        - Booking creation failed
    """
    pass


class PaymentException(AppException):
    """
    Exception raised for payment-related errors.
    
    Examples:
        - Invalid payment screenshot
        - Payment verification failed
        - Payment processing error
        - Missing payment information
    """
    pass


class PropertyException(AppException):
    """
    Exception raised for property-related errors.
    
    Examples:
        - Property not found
        - Invalid property data
        - Pricing not available
        - Property search failed
    """
    pass


class IntegrationException(AppException):
    """
    Exception raised for external integration errors.
    
    Examples:
        - WhatsApp API failure
        - Cloudinary upload error
        - Gemini API error
        - Network timeout
    """
    pass
