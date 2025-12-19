"""
Media URL extraction and processing utilities.

This module contains pure functions for working with media URLs,
particularly Cloudinary links.
"""

import re
from typing import Dict, List, Optional
from urllib.parse import urlparse


def extract_media_urls(text: str) -> Dict[str, List[str]]:
    """
    Extract media URLs from text.
    
    Extracts image and video URLs, particularly Cloudinary URLs.
    
    Args:
        text: Text containing media URLs
        
    Returns:
        Dictionary with 'images' and 'videos' lists
        
    Example:
        >>> extract_media_urls("Check this: https://res.cloudinary.com/image.jpg")
        {'images': ['https://res.cloudinary.com/image.jpg'], 'videos': []}
    """
    if not text:
        return {"images": [], "videos": []}
    
    images = []
    videos = []
    
    # Pattern for Cloudinary URLs
    cloudinary_pattern = r'https://res\.cloudinary\.com/[^\s]+'
    
    # Find all Cloudinary URLs
    cloudinary_urls = re.findall(cloudinary_pattern, text)
    
    for url in cloudinary_urls:
        # Determine if it's an image or video based on URL path
        if '/image/' in url or url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            if url not in images:
                images.append(url)
        elif '/video/' in url or url.endswith(('.mp4', '.mov', '.avi', '.webm')):
            if url not in videos:
                videos.append(url)
        else:
            # Default to image if unclear
            if url not in images:
                images.append(url)
    
    # Also look for other common image/video URLs
    general_image_pattern = r'https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp)'
    general_video_pattern = r'https?://[^\s]+\.(?:mp4|mov|avi|webm)'
    
    general_images = re.findall(general_image_pattern, text, re.IGNORECASE)
    general_videos = re.findall(general_video_pattern, text, re.IGNORECASE)
    
    # Add non-duplicate URLs
    for img in general_images:
        if img not in images:
            images.append(img)
    
    for vid in general_videos:
        if vid not in videos:
            videos.append(vid)
    
    return {"images": images, "videos": videos}


def remove_cloudinary_links(text: str) -> str:
    """
    Remove Cloudinary links from text.
    
    Args:
        text: Text containing Cloudinary links
        
    Returns:
        Text with Cloudinary links removed
        
    Example:
        >>> remove_cloudinary_links("Hello https://res.cloudinary.com/image.jpg world")
        'Hello  world'
    """
    if not text:
        return text
    
    # Pattern for Cloudinary URLs
    cloudinary_pattern = r'https://res\.cloudinary\.com/[^\s]+'
    
    # Remove Cloudinary URLs
    text = re.sub(cloudinary_pattern, '', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def detect_media_type(url: str) -> Optional[str]:
    """
    Detect media type from URL.
    
    Args:
        url: Media URL
        
    Returns:
        Media type: 'image', 'video', or None if unknown
        
    Example:
        >>> detect_media_type("https://example.com/photo.jpg")
        'image'
    """
    if not url:
        return None
    
    url_lower = url.lower()
    
    # Check for image extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']
    if any(url_lower.endswith(ext) for ext in image_extensions):
        return 'image'
    
    # Check for video extensions
    video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv']
    if any(url_lower.endswith(ext) for ext in video_extensions):
        return 'video'
    
    # Check Cloudinary URL patterns
    if 'cloudinary.com' in url_lower:
        if '/image/' in url_lower:
            return 'image'
        elif '/video/' in url_lower:
            return 'video'
    
    return None


def is_valid_url(url: str) -> bool:
    """
    Check if string is a valid URL.
    
    Args:
        url: String to check
        
    Returns:
        True if valid URL, False otherwise
        
    Example:
        >>> is_valid_url("https://example.com")
        True
    """
    if not url:
        return False
    
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def get_cloudinary_public_id(url: str) -> Optional[str]:
    """
    Extract Cloudinary public ID from URL.
    
    Args:
        url: Cloudinary URL
        
    Returns:
        Public ID or None if not a Cloudinary URL
        
    Example:
        >>> get_cloudinary_public_id("https://res.cloudinary.com/demo/image/upload/v1234/sample.jpg")
        'sample'
    """
    if not url or 'cloudinary.com' not in url:
        return None
    
    # Pattern to extract public ID from Cloudinary URL
    # Format: https://res.cloudinary.com/{cloud_name}/{resource_type}/upload/{version}/{public_id}.{format}
    pattern = r'cloudinary\.com/[^/]+/(?:image|video)/upload/(?:v\d+/)?([^/.]+)'
    
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    
    return None


def filter_media_urls(urls: List[str], media_type: Optional[str] = None) -> List[str]:
    """
    Filter list of URLs by media type.
    
    Args:
        urls: List of URLs to filter
        media_type: Type to filter by ('image', 'video', or None for all)
        
    Returns:
        Filtered list of URLs
        
    Example:
        >>> filter_media_urls(["img.jpg", "vid.mp4"], media_type='image')
        ['img.jpg']
    """
    if not urls:
        return []
    
    if not media_type:
        return urls
    
    return [url for url in urls if detect_media_type(url) == media_type]


def extract_all_urls(text: str) -> List[str]:
    """
    Extract all URLs from text.
    
    Args:
        text: Text containing URLs
        
    Returns:
        List of URLs
        
    Example:
        >>> extract_all_urls("Visit https://example.com and http://test.com")
        ['https://example.com', 'http://test.com']
    """
    if not text:
        return []
    
    # Pattern for URLs
    url_pattern = r'https?://[^\s]+'
    
    urls = re.findall(url_pattern, text)
    
    return urls
