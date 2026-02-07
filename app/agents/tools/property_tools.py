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


@tool("list_properties")
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


@tool("get_property_images")
def get_property_images(session_id: str) -> str:
    """
    CALL: user asks for images only or media
    NO CALL: user asks for videos or details

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


@tool("get_property_videos")
def get_property_videos(session_id: str) -> str:
    """
    CALL: user asks for videos only or media
    NO CALL: user asks for images or details

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


# Generic terms that should NOT be used for primary matching
GENERIC_TERMS = {
    # Property types
    'farmhouse', 'farm', 'hut', 'house', 'resort', 
    'villa', 'cottage', 'property', 'place',
    
    # Cities (add all your cities)
    'karachi', 'lahore', 'islamabad', 'rawalpindi', 
    'multan', 'faisalabad', 'peshawar', 'quetta',
    
    # Common words
    'the', 'a', 'an', 'and', 'or', 'in', 'at', 'on'
}


def _classify_words(text: str) -> tuple:
    """
    Classify words as significant or generic using fuzzy matching.
    
    Args:
        text: Input text to classify
        
    Returns:
        Tuple of (significant_words, generic_words)
    """
    words = text.lower().split()
    significant = []
    generic = []
    
    for word in words:
        is_generic = False
        
        # Fuzzy match against generic terms (0.7 threshold)
        for generic_term in GENERIC_TERMS:
            ratio = SequenceMatcher(None, word, generic_term).ratio()
            if ratio >= 0.7:
                generic.append(word)
                is_generic = True
                break
        
        if not is_generic:
            significant.append(word)
    
    return significant, generic


def _fuzzy_match_property_name(search_name: str, property_names: List[Dict]) -> Optional[Dict]:
    """
    Multi-stage fuzzy matching with tiebreaker and user confirmation.
    
    Algorithm:
    1. Separate user input word by word
    2. Fuzzy match each word with GENERIC_TERMS (threshold 0.7)
    3. Classify words as significant or generic
    4. Match user significant words with property significant words (threshold 0.6)
    5. If multiple properties match:
       a. Use generic words as tiebreaker
       b. If still tied, return multiple options for user confirmation
    
    Args:
        search_name: The name to search for
        property_names: List of dicts with 'name', 'property_id', 'city', 'type'
        
    Returns:
        - Single property dict if clear match
        - Dict with 'multiple_matches' key if ambiguous
        - None if no match
        
    Examples:
        "Seaside" → Matches "Seaside Farmhouse Karachi" ✅
        "Saeisde" → Matches "Seaside Farmhouse Karachi" ✅ (typo)
        "Karachi" → No match ❌ (generic term)
        "karcahi" → No match ❌ (typo of generic term)
        "Seaside Karachi" → Uses "Karachi" as tiebreaker if multiple "Seaside" properties
    """
    # STEP 1 & 2: Classify user words
    user_significant, user_generic = _classify_words(search_name)
    
    # If no significant words, return None
    if not user_significant:
        logger.info(f"Search '{search_name}' contains only generic terms")
        return None
    
    logger.info(f"User significant: {user_significant}, generic: {user_generic}")
    
    # STEP 3 & 4: Score each property based on significant words
    candidates = []
    
    for prop in property_names:
        prop_name = prop['name']
        prop_significant, prop_generic = _classify_words(prop_name)
        
        if not prop_significant:
            continue
        
        # Match user significant with property significant
        significant_score = 0
        matched_count = 0
        matched_words = []
        
        for user_word in user_significant:
            best_ratio = 0
            best_matched_word = None
            
            for prop_word in prop_significant:
                ratio = SequenceMatcher(None, user_word, prop_word).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_matched_word = prop_word
            
            if best_ratio >= 0.6:
                significant_score += best_ratio
                matched_count += 1
                matched_words.append(best_matched_word)
        
        # Only consider if at least one significant word matched
        if matched_count > 0:
            # Normalize by number of user significant words
            normalized_score = significant_score / len(user_significant)
            
            candidates.append({
                'property': prop,
                'significant_score': normalized_score,
                'matched_count': matched_count,
                'matched_words': matched_words,
                'prop_generic': prop_generic,
                'prop_significant': prop_significant
            })
            logger.info(f"Property '{prop_name}' scored {normalized_score:.2f} (matched: {matched_words})")
    
    if not candidates:
        logger.info(f"No matches found for '{search_name}'")
        return None
    
    # STEP 5: Check for ties
    # Sort by significant score
    candidates.sort(key=lambda x: (x['significant_score'], x['matched_count']), reverse=True)
    
    # Get top score
    top_score = candidates[0]['significant_score']
    
    # Find all candidates with top score (within 0.05 tolerance for ties)
    top_candidates = [c for c in candidates if abs(c['significant_score'] - top_score) < 0.05]
    
    # If only one top candidate, return it
    if len(top_candidates) == 1:
        logger.info(f"Single match: {top_candidates[0]['property']['name']}")
        return top_candidates[0]['property']
    
    # STEP 6: Tiebreaker using generic words
    if user_generic:
        logger.info(f"Tie detected ({len(top_candidates)} properties), using generic words as tiebreaker")
        
        for candidate in top_candidates:
            generic_score = 0
            
            for user_gen in user_generic:
                best_ratio = 0
                for prop_gen in candidate['prop_generic']:
                    ratio = SequenceMatcher(None, user_gen, prop_gen).ratio()
                    best_ratio = max(best_ratio, ratio)
                
                if best_ratio >= 0.6:
                    generic_score += best_ratio
            
            candidate['generic_score'] = generic_score
            logger.info(f"  {candidate['property']['name']}: generic score = {generic_score:.2f}")
        
        # Sort by generic score
        top_candidates.sort(key=lambda x: x.get('generic_score', 0), reverse=True)
        
        # Check if we have a clear winner (difference > 0.1)
        if len(top_candidates) > 1:
            if top_candidates[0].get('generic_score', 0) - top_candidates[1].get('generic_score', 0) > 0.1:
                logger.info(f"Winner by generic match: {top_candidates[0]['property']['name']}")
                return top_candidates[0]['property']
        elif top_candidates[0].get('generic_score', 0) > 0:
            logger.info(f"Winner by generic match: {top_candidates[0]['property']['name']}")
            return top_candidates[0]['property']
    
    # STEP 7: Still tied - return multiple options for user confirmation
    logger.info(f"Multiple matches found ({len(top_candidates)}), need user confirmation")
    return {
        'multiple_matches': True,
        'properties': [c['property'] for c in top_candidates[:3]]  # Max 3 options
    }



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
