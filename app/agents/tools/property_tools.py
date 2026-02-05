"""
Property-related agent tools.

This module contains tools for:
- Listing available properties
- Getting property details
- Getting property images
- Getting property videos
- Getting property ID from name

These tools use the PropertyService and SessionService layers for all business logic.
"""

import logging
from langchain.tools import tool
from typing import Dict, Optional, List
from datetime import datetime
from difflib import SequenceMatcher

from app.database import SessionLocal
from app.services.property_service import PropertyService
from app.services.session_service import SessionService
from app.repositories.property_repository import PropertyRepository
from app.repositories.booking_repository import BookingRepository
from app.repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)


@tool("list_properties", return_direct=True)
def list_properties(
    session_id: str,
    property_type: Optional[str] = None,
    city: str = "Karachi",
    country: str = "Pakistan",
    date: Optional[str] = None,
    day_of_the_week: Optional[str] = None,
    shift_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    max_occupancy: Optional[int] = None,
) -> dict:
    """
    CALL: user has provided or session has property_type, date, shift_type
    NO CALL: missing required info, session not found

    REQ:
    • session_id
    • property_type (hut/farm)
    • date (YYYY-MM-DD)
    • shift_type (Day, Night, Full Day, Full Night)

    RETURNS:
    ok {formatted list of available properties with price}
    err {error message or prompt for missing info}
    """
    db = SessionLocal()
    try:
        # Get session to check for stored values
        session_repo = SessionRepository()
        session = session_repo.get_by_id(db, session_id)
        
        if not session:
            return "Session not found. Please restart the conversation."
        
        # Use current parameter OR session value
        current_property_type = property_type or session.property_type
        if not current_property_type:
            return "🤔 Do you want to see huts or farmhouses?"
        
        # Check for required parameters - use current parameters OR session values
        current_date = date or (session.booking_date.strftime("%Y-%m-%d") if session.booking_date else None)
        current_shift_type = shift_type or session.shift_type
        
        if not current_date or not current_shift_type:
            return """**📅 Please provide the following details so we can find the best available farmhouse or hut for you:**

* **Date** of booking
* **Shift Type**: Day, Night, Full Day, or Full Night
* **Number of People**
* **Price Range** (Minimum and Maximum) (If applicable)"""
        
        # Parse booking date
        try:
            booking_date_obj = datetime.strptime(current_date, "%Y-%m-%d")
        except ValueError:
            return "❌ Invalid date format. Please use YYYY-MM-DD format."
        
        # Update session with new values (only if provided)
        session_service = SessionService(session_repo)
        update_data = {}
        if property_type:
            update_data["property_type"] = property_type
        if date:
            update_data["booking_date"] = booking_date_obj.date()
        if shift_type:
            update_data["shift_type"] = shift_type
        if min_price is not None:
            update_data["min_price"] = min_price
        if max_price is not None:
            update_data["max_price"] = max_price
        if max_occupancy is not None:
            update_data["max_occupancy"] = max_occupancy
        
        if update_data:
            session_service.update_session_data(db, session_id, **update_data)
        
        # Search properties using service
        property_service = PropertyService(
            PropertyRepository(),
            BookingRepository()
        )
        
        result = property_service.search_properties(
            db=db,
            property_type=current_property_type,
            booking_date=booking_date_obj,
            shift_type=current_shift_type,
            city=city,
            country=country,
            min_price=min_price,
            max_price=max_price,
            max_occupancy=max_occupancy,
            include_booked=False
        )
        
        if "error" in result:
            return result["error"]
        
        properties = result["properties"]
        
        if not properties:
            return f"❌ No {current_property_type}s available on {current_date} for {current_shift_type}."
        
        # Format date with day name
        formatted_date = booking_date_obj.strftime("%d-%B-%Y (%A)")
        
        # Property type display name
        property_display = "farmhouses" if current_property_type == "farm" else "huts"
        
        # Create numbered list
        numbered_lines = []
        for i, prop in enumerate(properties, 1):
            numbered_lines.append(f"{i}. {prop['name']}  Price (Rs) - {int(prop['price'])}")
        
        # Final message
        header = f"Available *{property_display}* and their *Price* for *{formatted_date} {current_shift_type}* shift:"
        message = header + "\n" + "\n\n".join(numbered_lines)
        message += f"\n\nAgr ap inme sy kisi {current_property_type} ki details ya pictures aur videos chahte hain to mujhe uska naam batayein! Shukriya."
        
        return message
        
    except Exception as e:
        logger.error(f"Error in list_properties tool: {e}", exc_info=True)
        return "Error searching properties. Please try again."
    finally:
        db.close()


@tool("get_property_pricing")
def get_property_pricing(session_id: str) -> str:
    """
    CALL: user asks about pricing specifically
    NO CALL: general property details, images/videos

    REQ:
    • session_id with property_id

    RETURNS:
    ok {pricing breakdown by day and shift}
    err {error message}
    """
    db = SessionLocal()
    try:
        # Get session to find property_id
        session_repo = SessionRepository()
        session = session_repo.get_by_id(db, session_id)
        
        if not session:
            return "Session not found. Please restart the conversation."
        
        if not session.property_id:
            return "Please provide property name first."
        
        # Get property details using service
        property_service = PropertyService(
            PropertyRepository(),
            BookingRepository()
        )
        
        result = property_service.get_property_details(
            db=db,
            property_id=str(session.property_id),
            include_media=False
        )
        
        if "error" in result:
            return result["error"]
        
        prop = result
        
        # Format ONLY pricing info
        if prop.get("pricing"):
            pricing_text = f"*Pricing for {prop['name']}:*\n\n"
            current_day = None
            for pricing in prop["pricing"]:
                day_of_week = pricing["day_of_week"]
                shift_type = pricing["shift_type"]
                price = pricing["price"]
                
                if current_day != day_of_week:
                    pricing_text += f"\n*{day_of_week.capitalize()}:*\n"
                    current_day = day_of_week
                pricing_text += f"  • {shift_type}: Rs.{int(price)}/-\n"
            
            return pricing_text
        else:
            return f"Pricing information not available for {prop['name']}. Please contact us for rates."
        
    except Exception as e:
        logger.error(f"Error in get_property_pricing tool: {e}", exc_info=True)
        return "Error retrieving pricing information. Please try again."
    finally:
        db.close()


@tool("get_property_details")
def get_property_details(session_id: str) -> str:
    """
    CALL: user asks for property info (location, amenities, description)
    NO CALL: pricing-only queries

    REQ:
    • session_id with property_id

    RETURNS:
    ok {detailed property info without pricing}
    err {error message}
    """
    db = SessionLocal()
    try:
        # Get session to find property_id
        session_repo = SessionRepository()
        session = session_repo.get_by_id(db, session_id)
        
        if not session:
            return "Session not found. Please restart the conversation."
        
        if not session.property_id:
            return "Please provide property name first."
        
        # Get property details using service
        property_service = PropertyService(
            PropertyRepository(),
            BookingRepository()
        )
        
        result = property_service.get_property_details(
            db=db,
            property_id=str(session.property_id),
            include_media=False
        )
        
        if "error" in result:
            return result["error"]
        
        prop = result
        
        # Format amenities
        amenities_list = prop.get("amenities", [])
        if amenities_list:
            amenities_text = ", ".join([a.get("value", "") for a in amenities_list if a.get("value")])
        else:
            amenities_text = "None listed"
        
        # Format property details WITHOUT pricing
        details_text = (
            f"*{prop['name']}*\n\n"
            f"📍 *Location:* {prop.get('address', 'N/A')}, {prop['city']}, {prop['country']}\n\n"
            f"👥 *Maximum Guests:* {prop['max_occupancy']} people\n\n"
            f"📝 *Description:* {prop.get('description', 'No description available')}\n\n"
            f"✨ *Amenities:* {amenities_text}"
        )
        
        return details_text
        
    except Exception as e:
        logger.error(f"Error in get_property_details tool: {e}", exc_info=True)
        return "Error retrieving property details. Please try again."
    finally:
        db.close()


@tool("get_property_media")
def get_property_media(session_id: str) -> str:
    """
    CALL: user asks for both images and videos
    NO CALL: images-only or videos-only

    REQ:
    • session_id with property_id

    RETURNS:
    ok {combined message with image and video URLs}
    err {error message}
    """
    db = SessionLocal()
    try:
        # Get session to find property_id
        session_repo = SessionRepository()
        session = session_repo.get_by_id(db, session_id)
        
        if not session:
            return "Session not found. Please restart the conversation."
        
        if not session.property_id:
            return "Please provide property name first."
        
        # Get property details for name
        property_service = PropertyService(
            PropertyRepository(),
            BookingRepository()
        )
        
        result = property_service.get_property_details(
            db=db,
            property_id=str(session.property_id),
            include_media=False
        )
        
        if "error" in result:
            return result["error"]
        
        property_name = result["name"]
        
        # Get both images and videos
        images = property_service.get_property_images(
            db=db,
            property_id=str(session.property_id)
        )
        
        videos = property_service.get_property_videos(
            db=db,
            property_id=str(session.property_id)
        )
        
        if not images and not videos:
            return f"No media available for {property_name}."
        
        # Format combined response
        response = f"Here are the images and videos of {property_name}:\n\n"
        
        if images:
            response += "Images:\n"
            for i, img_url in enumerate(images, 1):
                response += f"{i}. {img_url}\n"
            response += "\n"
        
        if videos:
            response += "Videos:\n"
            for i, video_url in enumerate(videos, 1):
                response += f"{i}. {video_url}\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in get_property_media tool: {e}", exc_info=True)
        return "Error retrieving property media. Please try again."
    finally:
        db.close()


@tool("get_property_images",return_direct=True)
def get_property_images(session_id: str) -> str:
    """
    CALL: user asks for images only
    NO CALL: user asks for videos or both media

    REQ:
    • session_id with property_id

    RETURNS:
    ok {image URLs}
    err {error message}
    """
    db = SessionLocal()
    try:
        # Get session to find property_id
        session_repo = SessionRepository()
        session = session_repo.get_by_id(db, session_id)
        
        if not session:
            return "Session not found. Please restart the conversation."
        
        if not session.property_id:
            return "Please provide property name first."
        
        # Get property images using service
        property_service = PropertyService(
            PropertyRepository(),
            BookingRepository()
        )
        
        images = property_service.get_property_images(
            db=db,
            property_id=str(session.property_id)
        )
        
        if not images:
            return "No images available for this property."
        
        # Get property name for better response
        property_service = PropertyService(
            PropertyRepository(),
            BookingRepository()
        )
        
        result = property_service.get_property_details(
            db=db,
            property_id=str(session.property_id),
            include_media=False
        )
        
        property_name = result.get("name", "this property") if "error" not in result else "this property"
        
        # Format response with descriptive text and URLs
        response = f"Here are the images for {property_name}:\n\n"
        for i, img_url in enumerate(images, 1):
            response += f"{i}. {img_url}\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in get_property_images tool: {e}", exc_info=True)
        return "Error retrieving property images. Please try again."
    finally:
        db.close()


@tool("get_property_videos",return_direct=True)
def get_property_videos(session_id: str) -> str:
    """
    CALL: user asks for videos only
    NO CALL: user asks for images or both media

    REQ:
    • session_id with property_id

    RETURNS:
    ok {video URLs}
    err {error message}
    """
    db = SessionLocal()
    try:
        # Get session to find property_id
        session_repo = SessionRepository()
        session = session_repo.get_by_id(db, session_id)
        
        if not session:
            return "Session not found. Please restart the conversation."
        
        if not session.property_id:
            return "Please provide property name first."
        
        # Get property videos using service
        property_service = PropertyService(
            PropertyRepository(),
            BookingRepository()
        )
        
        videos = property_service.get_property_videos(
            db=db,
            property_id=str(session.property_id)
        )
        
        if not videos:
            return "No videos available for this property."
        
        # Get property name for better response
        property_service = PropertyService(
            PropertyRepository(),
            BookingRepository()
        )
        
        result = property_service.get_property_details(
            db=db,
            property_id=str(session.property_id),
            include_media=False
        )
        
        property_name = result.get("name", "this property") if "error" not in result else "this property"
        
        # Format response with descriptive text and URLs
        response = f"Here are the videos for {property_name}:\n\n"
        for i, video_url in enumerate(videos, 1):
            response += f"{i}. {video_url}\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in get_property_videos tool: {e}", exc_info=True)
        return "Error retrieving property videos. Please try again."
    finally:
        db.close()


def _fuzzy_match_property_name(search_name: str, property_names: List[Dict]) -> Optional[Dict]:
    """
    Perform fuzzy matching on property names.
    
    Args:
        search_name: The name to search for
        property_names: List of dicts with 'name', 'property_id', 'city', 'type'
        
    Returns:
        Best matching property dict or None if no match above threshold
    """
    search_name_lower = search_name.lower().strip()
    matches = []
    
    for prop in property_names:
        prop_name_lower = prop['name'].lower().strip()
        
        # Calculate similarity ratio
        ratio = SequenceMatcher(None, search_name_lower, prop_name_lower).ratio()
        
        if ratio >= 0.6:  # Threshold of 0.6
            matches.append({
                'property': prop,
                'ratio': ratio
            })
    
    if not matches:
        return None
    
    # Sort by ratio (highest first) and return the top match
    matches.sort(key=lambda x: x['ratio'], reverse=True)
    return matches[0]['property']


@tool("get_property_id_from_name")
def get_property_id_from_name(session_id: str, property_name: str) -> str:
    """
    CALL: user provides property name (exact or fuzzy)
    NO CALL: any other property queries before providing name

    REQ:
    • session_id
    • property_name (string)

    RETURNS:
    ok {success message with property found}
    err {no match or error message}
    """
    db = SessionLocal()
    try:
        # Get session
        session_repo = SessionRepository()
        session = session_repo.get_by_id(db, session_id)
        
        if not session:
            return "Session not found. Please restart the conversation."
        
        # Get property type from session (if available)
        property_type = session.property_type if session.property_type else None
        
        # Get all property names based on type
        property_repo = PropertyRepository()
        
        if property_type:
            # Query properties of specific type
            sql = """
                SELECT property_id, name, city, type
                FROM properties
                WHERE type = :property_type
            """
            from sqlalchemy import text
            results = db.execute(text(sql), {"property_type": property_type}).fetchall()
        else:
            # Query all properties
            sql = """
                SELECT property_id, name, city, type
                FROM properties
            """
            from sqlalchemy import text
            results = db.execute(text(sql)).fetchall()
        
        # Convert to list of dicts
        property_names = [
            {
                'property_id': str(row[0]),
                'name': row[1],
                'city': row[2],
                'type': row[3]
            }
            for row in results
        ]
        
        if not property_names:
            return f"❌ No properties found{' of type ' + property_type if property_type else ''}."
        
        # Try exact match first
        exact_match = None
        search_name_lower = property_name.lower().strip()
        for prop in property_names:
            if prop['name'].lower().strip() == search_name_lower:
                exact_match = prop
                break
        
        # If exact match found, use it; otherwise use fuzzy matching
        if exact_match:
            matched_property = exact_match
            logger.info(f"Exact match found: {matched_property['name']}")
        else:
            matched_property = _fuzzy_match_property_name(property_name, property_names)
            if matched_property:
                logger.info(f"Fuzzy match found: {matched_property['name']} for search: {property_name}")
        
        if not matched_property:
            return f"❌ No property found matching '{property_name}'. Please check the name and try again."
        
        # Update session with property_id
        session_service = SessionService(session_repo)
        session_service.update_session_data(
            db=db,
            session_id=session_id,
            property_id=matched_property['property_id']
        )
        
        # Mark state change for memory system
        from app.agents.memory.state_detector import mark_state_change
        mark_state_change(session_id, db)
        
        return f"✅ Found: *{matched_property['name']}* in _{matched_property['city']}_"
        
    except Exception as e:
        logger.error(f"Error in get_property_id_from_name tool: {e}", exc_info=True)
        return "Error finding property. Please try again."
    finally:
        db.close()


# Export tools list for agent registration
property_tools = [
    list_properties,
    get_property_pricing,
    get_property_details,
    get_property_media,
    get_property_images,
    get_property_videos,
    get_property_id_from_name,
]

__all__ = [
    "list_properties",
    "get_property_pricing",
    "get_property_details",
    "get_property_media",
    "get_property_images",
    "get_property_videos",
    "get_property_id_from_name",
    "property_tools",
]
