# MediaService Integration Guide

## Overview
This guide shows how to integrate the MediaService into existing code to replace direct media handling logic.

## Quick Start

### Import the Service
```python
from app.services import MediaService

# Create instance
media_service = MediaService()
```

## Replacing Existing Code

### 1. Replace Direct Cloudinary Uploads

**Before:**
```python
from app.integrations.cloudinary import CloudinaryClient

cloudinary_client = CloudinaryClient()
url = await cloudinary_client.upload_base64(image_data, folder="payments")
```

**After:**
```python
from app.services import MediaService

media_service = MediaService()
result = await media_service.upload_image(
    image_data=image_data,
    is_base64=True,
    folder="payments"
)

if result["success"]:
    url = result["url"]
else:
    # Handle error
    print(result["error"])
```

### 2. Replace extract_media_urls() Function

**Before (in app/routers/web_routes.py):**
```python
def extract_media_urls(text: str) -> Optional[Dict[str, List[str]]]:
    pattern = r"https://[^\s]+"
    urls = re.findall(pattern, text)
    # ... rest of logic
```

**After:**
```python
from app.services import MediaService

media_service = MediaService()
urls = media_service.extract_media_urls(text)
```

### 3. Replace remove_cloudinary_links() Function

**Before (in app/routers/web_routes.py):**
```python
def remove_cloudinary_links(text: str) -> str:
    pattern = r"https?://res\.cloudinary\.com/[^\s]+(?:\.jpg|\.jpeg|\.png|\.mp4)"
    cleaned_text = re.sub(pattern, '', text)
    # ... rest of logic
```

**After:**
```python
from app.services import MediaService

media_service = MediaService()
cleaned_text = media_service.remove_media_links(text)
```

## Usage in Different Contexts

### In API Routes (FastAPI)
```python
from fastapi import APIRouter, Depends
from app.services import MediaService

router = APIRouter()

def get_media_service() -> MediaService:
    return MediaService()

@router.post("/upload")
async def upload_image(
    image_data: str,
    media_service: MediaService = Depends(get_media_service)
):
    result = await media_service.upload_image(
        image_data=image_data,
        is_base64=True,
        folder="uploads"
    )
    return result
```


### In Agent Tools
```python
from app.services import MediaService

media_service = MediaService()

def process_bot_response(response_text: str):
    # Extract media URLs
    media_urls = media_service.extract_media_urls(response_text)
    
    # Remove media links from text
    clean_text = media_service.remove_media_links(response_text)
    
    return {
        "text": clean_text,
        "media": media_urls
    }
```

### In Webhook Handlers
```python
from app.services import MediaService

async def handle_webhook(message: dict):
    media_service = MediaService()
    
    # Process bot response
    bot_response = generate_response(message)
    
    # Extract and handle media
    media_urls = media_service.extract_media_urls(bot_response)
    
    if media_urls:
        # Send media separately
        clean_text = media_service.remove_media_links(bot_response)
        await send_text(clean_text)
        await send_media(media_urls)
    else:
        await send_text(bot_response)
```

## Complete Workflow Example

```python
from app.services import MediaService

async def send_property_details(property_id: str, user_id: str):
    media_service = MediaService()
    
    # 1. Generate response with media URLs
    response = f"""
    Property Details:
    https://res.cloudinary.com/demo/image/upload/prop_{property_id}_1.jpg
    https://res.cloudinary.com/demo/image/upload/prop_{property_id}_2.jpg
    https://res.cloudinary.com/demo/video/upload/tour_{property_id}.mp4
    
    Beautiful 3-bedroom property!
    """
    
    # 2. Extract media URLs
    media_urls = media_service.extract_media_urls(response)
    
    # 3. Clean text for display
    clean_text = media_service.remove_media_links(response)
    
    # 4. Send to user
    await send_message(user_id, clean_text)
    
    if media_urls:
        for img_url in media_urls["images"]:
            await send_image(user_id, img_url)
        for vid_url in media_urls["videos"]:
            await send_video(user_id, vid_url)
```

## Testing with MediaService

```python
from unittest.mock import Mock, AsyncMock
from app.services import MediaService

def test_my_function():
    # Create mock media service
    mock_media_service = Mock(spec=MediaService)
    mock_media_service.extract_media_urls.return_value = {
        "images": ["https://example.com/img.jpg"],
        "videos": []
    }
    
    # Use in your test
    result = my_function(media_service=mock_media_service)
    
    # Verify
    mock_media_service.extract_media_urls.assert_called_once()
```

## Benefits of Using MediaService

1. **Centralized Logic**: All media operations in one place
2. **Easy Testing**: Mock the service instead of individual functions
3. **Consistent Behavior**: Same logic across all parts of the app
4. **Error Handling**: Built-in error handling and logging
5. **Maintainability**: Changes to media logic only need to be made once
6. **Type Safety**: Clear return types and parameters
7. **Documentation**: Well-documented methods with examples

## Migration Checklist

- [ ] Replace direct CloudinaryClient calls with MediaService.upload_image()
- [ ] Replace extract_media_urls() function calls with MediaService.extract_media_urls()
- [ ] Replace remove_cloudinary_links() calls with MediaService.remove_media_links()
- [ ] Update imports to use MediaService
- [ ] Update tests to mock MediaService
- [ ] Remove old utility functions after migration
- [ ] Update documentation to reference MediaService
