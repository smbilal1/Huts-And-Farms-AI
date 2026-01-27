"""
Test script to verify image and video URL extraction with REAL property data from database.

This tests with actual property ID: 18a8a89a-5ec2-415d-8247-af27efb6f288
"""

from app.database import SessionLocal
from app.repositories.property_repository import PropertyRepository
from app.services.property_service import PropertyService
from app.repositories.booking_repository import BookingRepository
from app.utils.media_utils import extract_media_urls


def test_real_property_media():
    """Test with actual property data from database"""
    
    property_id = ""
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("Testing with REAL Property Data from Database")
        print("=" * 70)
        print(f"\nProperty ID: {property_id}")
        print()
        
        # Get property service
        property_service = PropertyService(
            PropertyRepository(),
            BookingRepository()
        )
        
        # Get actual images from database
        print("📸 Fetching images from database...")
        images = property_service.get_property_images(
            db=db,
            property_id=property_id
        )
        print(f"   Found {len(images)} images in database")
        
        # Get actual videos from database
        print("🎥 Fetching videos from database...")
        videos = property_service.get_property_videos(
            db=db,
            property_id=property_id
        )
        print(f"   Found {len(videos)} videos in database")
        print()
        
        # Simulate what the tool returns
        tool_response = "Here are the images for this property:\n\n"
        for i, img_url in enumerate(images, 1):
            tool_response += f"{i}. {img_url}\n"
        
        tool_response += "\nAnd here are the videos:\n\n"
        for i, video_url in enumerate(videos, 1):
            tool_response += f"{i}. {video_url}\n"
        
        print("📝 Tool Response Format:")
        print("-" * 70)
        print(tool_response[:500] + "..." if len(tool_response) > 500 else tool_response)
        print("-" * 70)
        print()
        
        # Extract URLs using our fixed function
        print("🔍 Extracting URLs with fixed function...")
        result = extract_media_urls(tool_response)
        
        print(f"\n✅ Extraction Results:")
        print(f"   Images extracted: {len(result['images'])}")
        print(f"   Videos extracted: {len(result['videos'])}")
        print()
        
        # Verify counts match
        print("🧪 Running Verification Tests...")
        print()
        
        # Test 1: Count matches
        print("Test 1: Count Verification")
        print(f"   Expected images: {len(images)}")
        print(f"   Extracted images: {len(result['images'])}")
        assert len(result['images']) == len(images), f"Image count mismatch! Expected {len(images)}, got {len(result['images'])}"
        print("   ✅ Image count matches!")
        
        print(f"   Expected videos: {len(videos)}")
        print(f"   Extracted videos: {len(result['videos'])}")
        assert len(result['videos']) == len(videos), f"Video count mismatch! Expected {len(videos)}, got {len(result['videos'])}"
        print("   ✅ Video count matches!")
        print()
        
        # Test 2: No duplicates
        print("Test 2: Duplicate Check")
        unique_images = set(result['images'])
        unique_videos = set(result['videos'])
        print(f"   Unique images: {len(unique_images)}")
        print(f"   Unique videos: {len(unique_videos)}")
        assert len(result['images']) == len(unique_images), "Duplicate images found!"
        assert len(result['videos']) == len(unique_videos), "Duplicate videos found!"
        print("   ✅ No duplicates!")
        print()
        
        # Test 3: URL cleanliness
        print("Test 3: URL Cleanliness Check")
        all_clean = True
        
        print("   Checking images...")
        for i, img in enumerate(result['images'], 1):
            has_newline = '\n' in img
            has_trailing = any(img.endswith(f'\n{n}.') for n in range(1, 20))
            
            if has_newline or has_trailing:
                print(f"   ❌ Image {i} is BROKEN: {repr(img[:100])}")
                all_clean = False
            else:
                print(f"   ✅ Image {i} is clean")
        
        print("   Checking videos...")
        for i, vid in enumerate(result['videos'], 1):
            has_newline = '\n' in vid
            has_trailing = any(vid.endswith(f'\n{n}.') for n in range(1, 20))
            
            if has_newline or has_trailing:
                print(f"   ❌ Video {i} is BROKEN: {repr(vid[:100])}")
                all_clean = False
            else:
                print(f"   ✅ Video {i} is clean")
        
        assert all_clean, "Some URLs are not clean!"
        print("   ✅ All URLs are clean!")
        print()
        
        # Test 4: URLs match original
        print("Test 4: URL Matching")
        print("   Checking if extracted URLs match database URLs...")
        
        for i, original_img in enumerate(images, 1):
            if original_img in result['images']:
                print(f"   ✅ Image {i} matches")
            else:
                print(f"   ❌ Image {i} NOT FOUND in extracted URLs!")
                print(f"      Original: {original_img}")
                assert False, f"Image {i} from database not found in extracted URLs"
        
        for i, original_vid in enumerate(videos, 1):
            if original_vid in result['videos']:
                print(f"   ✅ Video {i} matches")
            else:
                print(f"   ❌ Video {i} NOT FOUND in extracted URLs!")
                print(f"      Original: {original_vid}")
                assert False, f"Video {i} from database not found in extracted URLs"
        
        print("   ✅ All URLs match!")
        print()
        
        # Display results
        print("=" * 70)
        print("📊 DETAILED RESULTS")
        print("=" * 70)
        print()
        
        print("📸 Extracted Images:")
        for i, img in enumerate(result['images'], 1):
            print(f"   {i}. {img}")
        print()
        
        print("🎥 Extracted Videos:")
        for i, vid in enumerate(result['videos'], 1):
            print(f"   {i}. {vid}")
        print()
        
        print("=" * 70)
        print("🎉 ALL TESTS PASSED WITH REAL DATABASE DATA!")
        print("=" * 70)
        print()
        print("✅ Summary:")
        print(f"   - {len(images)} images extracted correctly (no duplicates)")
        print(f"   - {len(videos)} videos extracted correctly (no duplicates)")
        print("   - All URLs are clean (no \\n or trailing text)")
        print("   - All URLs match database records")
        print()
        
    except AssertionError as e:
        print()
        print("=" * 70)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 70)
        raise
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    test_real_property_media()
