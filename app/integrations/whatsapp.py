"""
WhatsApp Business API integration client.

This module provides a client for sending messages and media through the
WhatsApp Business API (Meta Graph API).
"""

import httpx
import time
from typing import Dict, List, Optional, Any
from app.core.config import settings


class WhatsAppClient:
    """
    Client for WhatsApp Business API operations.
    
    Handles sending text messages and media (images/videos) through the
    Meta Graph API with automatic retry logic and error handling.
    """
    
    def __init__(self):
        """Initialize WhatsApp client with configuration from settings."""
        self.token = settings.META_ACCESS_TOKEN
        self.phone_number_id = settings.META_PHONE_NUMBER_ID
        self.base_url = f"https://graph.facebook.com/v23.0/{self.phone_number_id}/messages"
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.timeout = 10  # seconds
    
    async def send_message(
        self,
        recipient: str,
        message: str,
        media_urls: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp message with optional media attachments.
        
        Args:
            recipient: Phone number to send message to (with country code, no +)
            message: Text message content
            media_urls: Optional dict with 'images' and/or 'videos' keys containing URL lists
                       Example: {"images": ["url1", "url2"], "videos": ["url3"]}
        
        Returns:
            Dict containing:
                - success (bool): Whether the message was sent successfully
                - message_id (str): WhatsApp message ID if successful
                - error (str): Error message if failed
        
        Example:
            >>> client = WhatsAppClient()
            >>> result = await client.send_message(
            ...     recipient="923001234567",
            ...     message="Hello!",
            ...     media_urls={"images": ["https://example.com/image.jpg"]}
            ... )
            >>> print(result["success"])
            True
        """
        try:
            # Send media first if provided
            if media_urls:
                media_result = await self.send_media(recipient, media_urls)
                if not media_result["success"]:
                    return media_result
            
            # Send text message if there's content
            if message and message.strip():
                return await self._send_text_message(recipient, message)
            
            # If only media was sent and no text
            if media_urls and (not message or not message.strip()):
                return {
                    "success": True,
                    "message_id": "media_only",
                    "message": "Media sent successfully"
                }
            
            return {
                "success": False,
                "error": "No message content or media provided"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def send_media(
        self,
        recipient: str,
        media_urls: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Send media files (images/videos) to a WhatsApp recipient.
        
        Args:
            recipient: Phone number to send media to (with country code, no +)
            media_urls: Dict with 'images' and/or 'videos' keys containing URL lists
                       Example: {"images": ["url1"], "videos": ["url2"]}
        
        Returns:
            Dict containing:
                - success (bool): Whether all media was sent successfully
                - sent_count (int): Number of media files sent
                - failed_count (int): Number of media files that failed
                - errors (list): List of error messages for failed media
        
        Example:
            >>> client = WhatsAppClient()
            >>> result = await client.send_media(
            ...     recipient="923001234567",
            ...     media_urls={"images": ["https://example.com/img.jpg"]}
            ... )
        """
        if not media_urls:
            return {
                "success": False,
                "error": "No media URLs provided"
            }
        
        sent_count = 0
        failed_count = 0
        errors = []
        
        try:
            # Process each media type
            for media_type, urls in media_urls.items():
                if not urls:
                    continue
                
                # Convert 'images' to 'image' and 'videos' to 'video' for WhatsApp API
                whatsapp_media_type = media_type.rstrip('s')  # Remove trailing 's'
                
                # Validate media type
                if whatsapp_media_type not in ['image', 'video']:
                    errors.append(f"Invalid media type: {media_type}")
                    failed_count += len(urls)
                    continue
                
                # Send each media file
                for media_url in urls:
                    result = await self._send_single_media(
                        recipient,
                        media_url,
                        whatsapp_media_type
                    )
                    
                    if result["success"]:
                        sent_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"{whatsapp_media_type} {media_url}: {result.get('error', 'Unknown error')}")
            
            return {
                "success": failed_count == 0,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "errors": errors if errors else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "error": f"Media sending error: {str(e)}",
                "errors": errors
            }
    
    async def _send_text_message(
        self,
        recipient: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Internal method to send a text message with retry logic.
        
        Args:
            recipient: Phone number to send message to
            message: Text message content
        
        Returns:
            Dict with success status and message_id or error
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message}
        }
        
        # Retry logic
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.base_url,
                        json=payload,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        message_id = data.get("messages", [{}])[0].get("id", "")
                        return {
                            "success": True,
                            "message_id": message_id
                        }
                    else:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        
                        # Don't retry on client errors (4xx)
                        if 400 <= response.status_code < 500:
                            return {
                                "success": False,
                                "error": error_msg
                            }
                        
                        # Retry on server errors (5xx)
                        if attempt < self.max_retries - 1:
                            await self._wait_before_retry(attempt)
                            continue
                        
                        return {
                            "success": False,
                            "error": error_msg
                        }
            
            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    await self._wait_before_retry(attempt)
                    continue
                return {
                    "success": False,
                    "error": "Request timeout after retries"
                }
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    await self._wait_before_retry(attempt)
                    continue
                return {
                    "success": False,
                    "error": f"Request failed: {str(e)}"
                }
        
        return {
            "success": False,
            "error": "Max retries exceeded"
        }
    
    async def _send_single_media(
        self,
        recipient: str,
        media_url: str,
        media_type: str
    ) -> Dict[str, Any]:
        """
        Internal method to send a single media file with retry logic.
        
        Args:
            recipient: Phone number to send media to
            media_url: URL of the media file
            media_type: 'image' or 'video'
        
        Returns:
            Dict with success status and message_id or error
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": media_type,
            media_type: {
                "link": media_url
            }
        }
        
        # Retry logic
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.base_url,
                        json=payload,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        message_id = data.get("messages", [{}])[0].get("id", "")
                        return {
                            "success": True,
                            "message_id": message_id
                        }
                    else:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        
                        # Don't retry on client errors (4xx)
                        if 400 <= response.status_code < 500:
                            return {
                                "success": False,
                                "error": error_msg
                            }
                        
                        # Retry on server errors (5xx)
                        if attempt < self.max_retries - 1:
                            await self._wait_before_retry(attempt)
                            continue
                        
                        return {
                            "success": False,
                            "error": error_msg
                        }
            
            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    await self._wait_before_retry(attempt)
                    continue
                return {
                    "success": False,
                    "error": f"{media_type} timeout after retries"
                }
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    await self._wait_before_retry(attempt)
                    continue
                return {
                    "success": False,
                    "error": f"{media_type} request failed: {str(e)}"
                }
        
        return {
            "success": False,
            "error": f"{media_type} max retries exceeded"
        }
    
    async def _wait_before_retry(self, attempt: int) -> None:
        """
        Wait before retrying with exponential backoff.
        
        Args:
            attempt: Current attempt number (0-indexed)
        """
        wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
        await asyncio.sleep(wait_time)


# Import asyncio at the end to avoid circular import issues
import asyncio
