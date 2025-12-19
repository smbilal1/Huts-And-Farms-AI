"""
Media service for business logic related to media handling.

This module provides the MediaService class that implements all media-related
business logic including image uploads, media URL extraction, and media link removal.
"""

import logging
from typing import Dict, List, Optional, Any
from app.integrations.cloudinary import CloudinaryClient
from app.utils.media_utils import (
    extract_media_urls as extract_urls,
    remove_cloudinary_links as remove_links,
    detect_media_type
)

logger = logging.getLogger(__name__)


class MediaService:
    """
    Service for managing media operations.
    
    Handles all media-related business logic including uploading images,
    extracting media URLs from text, and removing media links from text.
    """
    
    def __init__(
        self,
        cloudinary_client: Optional[CloudinaryClient] = None
    ):
        """
        Initialize the media service with client dependencies.
        
        Args:
            cloudinary_client: Client for media upload operations
        """
        self.cloudinary_client = cloudinary_client or CloudinaryClient()
    
    async def upload_image(
        self,
        image_data: str,
        is_base64: bool = True,
        folder: Optional[str] = None,
        public_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload an image to Cloudinary.
        
        Args:
            image_data: Base64 encoded image string or image URL
            is_base64: Whether the image_data is base64 encoded (True) or URL (False)
            folder: Optional folder path in Cloudinary to organize uploads
            public_id: Optional custom public ID for the uploaded image
        
        Returns:
            Dict containing:
                - success: Boolean indicating if upload was successful
                - url: Secure URL of uploaded image (if successful)
                - error: Error message (if failed)
        
        Example:
            >>> service = MediaService()
            >>> result = await service.upload_image(
            ...     image_data="iVBORw0KGgoAAAANSUhEUgAAAAUA...",
            ...     is_base64=True,
            ...     folder="payment_screenshots"
            ... )
            >>> print(result["url"])
            'https://res.cloudinary.com/...'
        """
        try:
            if is_base64:
                logger.info(f"Uploading base64 image to folder: {folder}")
                url = await self.cloudinary_client.upload_base64(
                    image_data=image_data,
                    folder=folder,
                    public_id=public_id
                )
            else:
                logger.info(f"Uploading image from URL to folder: {folder}")
                url = await self.cloudinary_client.upload_url(
                    image_url=image_data,
                    folder=folder,
                    public_id=public_id
                )
            
            logger.info(f"Image uploaded successfully: {url}")
            return {
                "success": True,
                "url": url
            }
            
        except ValueError as e:
            logger.error(f"Validation error uploading image: {str(e)}")
            return {
                "success": False,
                "error": f"Invalid image data: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Failed to upload image: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Upload failed: {str(e)}"
            }
    
    def extract_media_urls(self, text: str) -> Optional[Dict[str, List[str]]]:
        """
        Extract all media URLs from text.
        
        Identifies and categorizes URLs as images or videos based on URL patterns.
        Specifically looks for Cloudinary URLs with /image/ or /video/ paths.
        
        Args:
            text: Text content to extract media URLs from
        
        Returns:
            Dict containing:
                - images: List of image URLs
                - videos: List of video URLs
            Returns None if no media URLs found
        
        Example:
            >>> service = MediaService()
            >>> text = "Check this out: https://res.cloudinary.com/demo/image/upload/sample.jpg"
            >>> urls = service.extract_media_urls(text)
            >>> print(urls["images"])
            ['https://res.cloudinary.com/demo/image/upload/sample.jpg']
        """
        if not text:
            return None
        
        # Use utility function to extract media URLs
        media = extract_urls(text)
        
        # Return None if no media URLs found
        if not media["images"] and not media["videos"]:
            return None
        
        logger.debug(f"Extracted {len(media['images'])} images and {len(media['videos'])} videos from text")
        return media
    
    def remove_media_links(self, text: str) -> str:
        """
        Remove Cloudinary media links from text.
        
        Removes all Cloudinary URLs (images and videos) from the text and cleans up
        any resulting empty lines or extra whitespace.
        
        Args:
            text: Text content to remove media links from
        
        Returns:
            Cleaned text with media links removed
        
        Example:
            >>> service = MediaService()
            >>> text = "Here's the image: https://res.cloudinary.com/demo/image/upload/sample.jpg\\nLooks good!"
            >>> cleaned = service.remove_media_links(text)
            >>> print(cleaned)
            "Here's the image:\\nLooks good!"
        """
        if not text:
            return text
        
        # Use utility function to remove Cloudinary links
        cleaned_text = remove_links(text)
        
        logger.debug("Removed media links from text")
        return cleaned_text
    
    def get_media_type(self, url: str) -> Optional[str]:
        """
        Determine the media type from a URL.
        
        Args:
            url: Media URL to analyze
        
        Returns:
            'image', 'video', or None if type cannot be determined
        
        Example:
            >>> service = MediaService()
            >>> media_type = service.get_media_type("https://res.cloudinary.com/demo/image/upload/sample.jpg")
            >>> print(media_type)
            'image'
        """
        # Use utility function to detect media type
        return detect_media_type(url)
