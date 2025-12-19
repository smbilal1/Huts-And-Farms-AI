"""
Application constants.
Centralized location for all hardcoded values used throughout the application.
"""

import uuid

# Payment Configuration
EASYPAISA_NUMBER = "03155699929"
EASYPAISA_ACCOUNT_HOLDER = "SYED MUHAMMAD BILAL"

# Admin Configuration
VERIFICATION_WHATSAPP = "923155699929"
WEB_ADMIN_USER_ID = uuid.UUID("216d5ab6-e8ef-4a5c-8b7c-45be19b28334")

# Webhook Configuration
VERIFY_TOKEN = "my_custom_secret_token"

# Session Configuration
SESSION_INACTIVITY_TIMEOUT_HOURS = 1  # Hours before session expires
BOOKING_PENDING_TIMEOUT_MINUTES = 30  # Minutes before pending booking expires

# Application Configuration
APP_NAME = "HutBuddy"

# Booking Configuration
VALID_SHIFT_TYPES = ["Day", "Night", "Full Day", "Full Night"]
VALID_PROPERTY_TYPES = ["hut", "farm"]
VALID_BOOKING_STATUSES = ["Pending", "Waiting", "Confirmed", "Cancelled", "Completed", "Expired"]
VALID_BOOKING_SOURCES = ["Website", "Bot", "Third-Party"]

# Location Defaults
DEFAULT_CITY = "Karachi"
DEFAULT_COUNTRY = "Pakistan"

# Message Limits
HOURLY_MESSAGE_LIMIT = 100  # Maximum messages per hour per user
HOURLY_TOKEN_LIMIT = 10000  # Maximum tokens per hour per user

# Database Configuration
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10
DB_POOL_RECYCLE_SECONDS = 3600
DB_POOL_TIMEOUT_SECONDS = 30
DB_CONNECT_TIMEOUT_SECONDS = 30

# API Configuration
WHATSAPP_API_VERSION = "v23.0"
WHATSAPP_API_TIMEOUT_SECONDS = 10

# Media Configuration
SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png"]
SUPPORTED_VIDEO_FORMATS = [".mp4"]

# Validation
CNIC_LENGTH = 13
MIN_NAME_LENGTH = 2
MIN_PHONE_LENGTH = 10

# Export all constants
__all__ = [
    "EASYPAISA_NUMBER",
    "EASYPAISA_ACCOUNT_HOLDER",
    "VERIFICATION_WHATSAPP",
    "WEB_ADMIN_USER_ID",
    "VERIFY_TOKEN",
    "SESSION_INACTIVITY_TIMEOUT_HOURS",
    "BOOKING_PENDING_TIMEOUT_MINUTES",
    "APP_NAME",
    "VALID_SHIFT_TYPES",
    "VALID_PROPERTY_TYPES",
    "VALID_BOOKING_STATUSES",
    "VALID_BOOKING_SOURCES",
    "DEFAULT_CITY",
    "DEFAULT_COUNTRY",
    "HOURLY_MESSAGE_LIMIT",
    "HOURLY_TOKEN_LIMIT",
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "DB_POOL_RECYCLE_SECONDS",
    "DB_POOL_TIMEOUT_SECONDS",
    "DB_CONNECT_TIMEOUT_SECONDS",
    "WHATSAPP_API_VERSION",
    "WHATSAPP_API_TIMEOUT_SECONDS",
    "SUPPORTED_IMAGE_FORMATS",
    "SUPPORTED_VIDEO_FORMATS",
    "CNIC_LENGTH",
    "MIN_NAME_LENGTH",
    "MIN_PHONE_LENGTH",
]
