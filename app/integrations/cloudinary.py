"""
Cloudinary integration client.

This module provides a client for uploading images and media to Cloudinary
cloud storage service.
"""

import cloudinary
import cloudinary.uploader
import base64
import asyncio
from typing import Dict, Any, Optional
from app.core.config import settings


class CloudinaryClient:
    """
    Client for Cloudinary media upload operations.
    
    Handles uploading images from base64 data or URLs to Cloudinary
    with error handling and configuration management.
    """
    
    def __init__(self):
        """Initialize Cloudinary client with configuration from settings."""
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
        self.timeout = 30  # seconds for upload operations
    
    async def upload_base64(
        self,
        image_data: str,
        folder: Optional[str] = None,
        public_id: Optional[str] = None
    ) -> str:
        """
        Upload a base64 encoded image to Cloudinary.
        
        Args:
            image_data: Base64 encoded image string (with or without data URI prefix)
            folder: Optional folder path in Cloudinary to organize uploads
            public_id: Optional custom public ID for the uploaded image
        
        Returns:
            str: Secure URL of the uploaded image
        
        Raises:
            ValueError: If image_data is invalid or empty
            Exception: If upload fails after processing
        
        Example:
            >>> client = CloudinaryClient()
            >>> url = await client.upload_base64(
            ...     image_data="iVBORw0KGgoAAAANSUhEUgAAAAUA...",
            ...     folder="payment_screenshots"
            ... )
            >>> print(url)
            'https://res.cloudinary.com/...'
        """
        if not image_data:
            raise ValueError("image_data cannot be empty")
        
        try:
            # Remove data URI prefix if present (e.g., "data:image/png;base64,")
            if "," in image_data and image_data.startswith("data:"):
                image_data = image_data.split(",", 1)[1]
            
            # Decode base64 to bytes
            try:
                image_bytes = base64.b64decode(image_data)
            except Exception as e:
                raise ValueError(f"Invalid base64 data: {str(e)}")
            
            if len(image_bytes) == 0:
                raise ValueError("Decoded image data is empty")
            
            # Prepare upload options
            upload_options = {}
            if folder:
                upload_options["folder"] = folder
            if public_id:
                upload_options["public_id"] = public_id
            
            # Upload to Cloudinary (run in thread pool since it's blocking)
            result = await asyncio.to_thread(
                cloudinary.uploader.upload,
                image_bytes,
                **upload_options
            )
            
            # Extract secure URL from result
            secure_url = result.get("secure_url")
            if not secure_url:
                raise Exception("Upload succeeded but no secure_url in response")
            
            return secure_url
            
        except ValueError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            raise Exception(f"Failed to upload base64 image: {str(e)}")
    
    async def upload_url(
        self,
        image_url: str,
        folder: Optional[str] = None,
        public_id: Optional[str] = None
    ) -> str:
        """
        Upload an image from a URL to Cloudinary.
        
        Args:
            image_url: URL of the image to upload
            folder: Optional folder path in Cloudinary to organize uploads
            public_id: Optional custom public ID for the uploaded image
        
        Returns:
            str: Secure URL of the uploaded image
        
        Raises:
            ValueError: If image_url is invalid or empty
            Exception: If upload fails
        
        Example:
            >>> client = CloudinaryClient()
            >>> url = await client.upload_url(
            ...     image_url="https://example.com/image.jpg",
            ...     folder="property_images"
            ... )
            >>> print(url)
            'https://res.cloudinary.com/...'
        """
        if not image_url:
            raise ValueError("image_url cannot be empty")
        
        if not image_url.startswith(("http://", "https://")):
            raise ValueError("image_url must be a valid HTTP/HTTPS URL")
        
        try:
            # Prepare upload options
            upload_options = {}
            if folder:
                upload_options["folder"] = folder
            if public_id:
                upload_options["public_id"] = public_id
            
            # Upload to Cloudinary (run in thread pool since it's blocking)
            result = await asyncio.to_thread(
                cloudinary.uploader.upload,
                image_url,
                **upload_options
            )
            
            # Extract secure URL from result
            secure_url = result.get("secure_url")
            if not secure_url:
                raise Exception("Upload succeeded but no secure_url in response")
            
            return secure_url
            
        except ValueError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            raise Exception(f"Failed to upload image from URL: {str(e)}")
    
    async def upload_file(
        self,
        file_path: str,
        folder: Optional[str] = None,
        public_id: Optional[str] = None,
        resource_type: str = "image"
    ) -> str:
        """
        Upload a file from local filesystem to Cloudinary.
        
        Args:
            file_path: Path to the file to upload
            folder: Optional folder path in Cloudinary to organize uploads
            public_id: Optional custom public ID for the uploaded file
            resource_type: Type of resource ('image', 'video', 'raw', 'auto')
        
        Returns:
            str: Secure URL of the uploaded file
        
        Raises:
            ValueError: If file_path is invalid or file doesn't exist
            Exception: If upload fails
        
        Example:
            >>> client = CloudinaryClient()
            >>> url = await client.upload_file(
            ...     file_path="/path/to/image.jpg",
            ...     folder="uploads"
            ... )
        """
        if not file_path:
            raise ValueError("file_path cannot be empty")
        
        try:
            # Prepare upload options
            upload_options = {"resource_type": resource_type}
            if folder:
                upload_options["folder"] = folder
            if public_id:
                upload_options["public_id"] = public_id
            
            # Upload to Cloudinary (run in thread pool since it's blocking)
            result = await asyncio.to_thread(
                cloudinary.uploader.upload,
                file_path,
                **upload_options
            )
            
            # Extract secure URL from result
            secure_url = result.get("secure_url")
            if not secure_url:
                raise Exception("Upload succeeded but no secure_url in response")
            
            return secure_url
            
        except ValueError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            raise Exception(f"Failed to upload file: {str(e)}")
    
    def get_upload_info(self) -> Dict[str, Any]:
        """
        Get current Cloudinary configuration info (without sensitive data).
        
        Returns:
            Dict containing cloud name and configuration status
        
        Example:
            >>> client = CloudinaryClient()
            >>> info = client.get_upload_info()
            >>> print(info["cloud_name"])
            'my-cloud'
        """
        return {
            "cloud_name": settings.CLOUDINARY_CLOUD_NAME,
            "configured": bool(
                settings.CLOUDINARY_CLOUD_NAME and
                settings.CLOUDINARY_API_KEY and
                settings.CLOUDINARY_API_SECRET
            )
        }
