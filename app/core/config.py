"""
Core configuration module using Pydantic Settings.
Centralizes all environment variables and provides type-safe configuration access.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All required settings will raise an error if not provided.
    """
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL database connection URL"
    )
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(
        ...,
        description="OpenAI API key for GPT models"
    )
    
    # Google AI Configuration (optional, used for payment screenshot analysis)
    GOOGLE_API_KEY: Optional[str] = Field(
        None,
        description="Google Generative AI API key for Gemini models (optional, used for payment processing)"
    )
    
    # Meta/WhatsApp Configuration
    META_ACCESS_TOKEN: str = Field(
        ...,
        description="Meta (Facebook) access token for WhatsApp Business API"
    )
    
    META_PHONE_NUMBER_ID: str = Field(
        ...,
        description="WhatsApp Business phone number ID"
    )
    
    META_VERIFY_TOKEN: str = Field(
        default="my_custom_secret_token",
        description="Webhook verification token for Meta"
    )
    
    # Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME: str = Field(
        ...,
        description="Cloudinary cloud name"
    )
    
    CLOUDINARY_API_KEY: str = Field(
        ...,
        description="Cloudinary API key"
    )
    
    CLOUDINARY_API_SECRET: str = Field(
        ...,
        description="Cloudinary API secret"
    )
    
    CLOUDINARY_URL: Optional[str] = Field(
        None,
        description="Cloudinary connection URL (optional, can be constructed from other fields)"
    )
    
    # Ngrok Configuration (Development)
    NGROK_AUTH_TOKEN: Optional[str] = Field(
        None,
        description="Ngrok authentication token for local development tunneling"
    )
    
    # Admin Webhook Configuration
    ADMIN_WEBHOOK_URL: Optional[str] = Field(
        default="",
        description="Webhook URL for admin notifications"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"  # Ignore extra fields in .env file
    }
    
    @field_validator("SQLALCHEMY_DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v):
        """Validate database URL format"""
        if not v:
            raise ValueError("SQLALCHEMY_DATABASE_URL is required")
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("SQLALCHEMY_DATABASE_URL must be a PostgreSQL connection string")
        return v
    
    @field_validator("META_ACCESS_TOKEN", "META_PHONE_NUMBER_ID")
    @classmethod
    def validate_meta_config(cls, v, info):
        """Validate Meta/WhatsApp configuration"""
        if not v:
            raise ValueError(f"{info.field_name} is required for WhatsApp integration")
        return v
    
    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_api_key(cls, v):
        """Validate OpenAI API key"""
        if not v:
            raise ValueError("OPENAI_API_KEY is required for AI agent integration")
        return v
    
    @field_validator("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
    @classmethod
    def validate_cloudinary_config(cls, v, info):
        """Validate Cloudinary configuration"""
        if not v:
            raise ValueError(f"{info.field_name} is required for Cloudinary integration")
        return v
    
    def get_cloudinary_url(self) -> str:
        """
        Construct Cloudinary URL from components if not provided directly.
        Format: cloudinary://API_KEY:API_SECRET@CLOUD_NAME
        """
        if self.CLOUDINARY_URL:
            return self.CLOUDINARY_URL
        return f"cloudinary://{self.CLOUDINARY_API_KEY}:{self.CLOUDINARY_API_SECRET}@{self.CLOUDINARY_CLOUD_NAME}"


# Create a singleton instance of settings
# This will be imported throughout the application
try:
    settings = Settings()
except Exception as e:
    print(f"❌ Error loading configuration: {e}")
    print("Please ensure all required environment variables are set in your .env file")
    raise


# Export settings instance
__all__ = ["settings", "Settings"]
