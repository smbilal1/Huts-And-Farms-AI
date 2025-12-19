# Core Configuration Module

This module provides centralized configuration management for the application using Pydantic Settings.

## Files

- **`config.py`**: Environment variable configuration using Pydantic Settings
- **`constants.py`**: Application constants (hardcoded values)
- **`__init__.py`**: Module initialization

## Usage

### Importing Configuration

```python
from app.core.config import settings

# Access environment variables
database_url = settings.SQLALCHEMY_DATABASE_URL
api_key = settings.GOOGLE_API_KEY
whatsapp_token = settings.META_ACCESS_TOKEN
```

### Importing Constants

```python
from app.core.constants import (
    EASYPAISA_NUMBER,
    WEB_ADMIN_USER_ID,
    VERIFICATION_WHATSAPP,
    VALID_SHIFT_TYPES
)

# Use constants
payment_number = EASYPAISA_NUMBER
admin_id = WEB_ADMIN_USER_ID
```

## Configuration Validation

The `Settings` class automatically validates all required environment variables on startup:

- **Database**: `SQLALCHEMY_DATABASE_URL` (must be PostgreSQL)
- **Google AI**: `GOOGLE_API_KEY` (required)
- **Meta/WhatsApp**: `META_ACCESS_TOKEN`, `META_PHONE_NUMBER_ID` (required)
- **Cloudinary**: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` (required)

If any required variable is missing, the application will fail to start with a clear error message.

## Environment Variables

All environment variables should be defined in the `.env` file at the project root:

```env
# Database
SQLALCHEMY_DATABASE_URL=postgresql://user:pass@host/db

# Google AI
GOOGLE_API_KEY=your_google_api_key

# Meta/WhatsApp
META_ACCESS_TOKEN=your_meta_token
META_PHONE_NUMBER_ID=your_phone_id
META_VERIFY_TOKEN=my_custom_secret_token

# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Optional
OPENAI_API_KEY=your_openai_key
NGROK_AUTH_TOKEN=your_ngrok_token
ADMIN_WEBHOOK_URL=your_webhook_url
```

## Benefits

1. **Type Safety**: All configuration values are type-checked
2. **Validation**: Required fields are validated on startup
3. **Centralization**: Single source of truth for all configuration
4. **Documentation**: Field descriptions explain each setting
5. **IDE Support**: Auto-completion and type hints in IDEs

## Migration from os.getenv()

**Before:**
```python
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("META_ACCESS_TOKEN")
```

**After:**
```python
from app.core.config import settings

TOKEN = settings.META_ACCESS_TOKEN
```

## Adding New Configuration

To add a new environment variable:

1. Add it to the `Settings` class in `config.py`:
```python
NEW_SETTING: str = Field(
    ...,  # Required, or provide default value
    description="Description of the setting"
)
```

2. Add validation if needed:
```python
@field_validator("NEW_SETTING")
@classmethod
def validate_new_setting(cls, v):
    if not v:
        raise ValueError("NEW_SETTING is required")
    return v
```

3. Add it to your `.env` file:
```env
NEW_SETTING=value
```

## Adding New Constants

To add a new constant, simply add it to `constants.py`:

```python
# New constant
MY_CONSTANT = "value"

# Add to __all__ for exports
__all__ = [
    # ... existing exports
    "MY_CONSTANT",
]
```
