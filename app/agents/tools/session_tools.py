"""
Session management tools for updating user preferences.

This module contains tools for:
- Setting property type, date, shift, price range, occupancy
- Providing helpful feedback on what's been set and what's still needed
"""

import logging
from langchain.tools import tool
from typing import Optional
from datetime import datetime

from app.database import SessionLocal
from app.services.session_service import SessionService
from app.repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)


@tool("set_booking_preferences")
def set_booking_preferences(
    session_id: str,
    property_type: Optional[str] = None,
    booking_date: Optional[str] = None,
    shift_type: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    max_occupancy: Optional[int] = None
) -> str:
    """
    CALL: user provides preferences (property type, date, shift, price, guests)
    NO CALL: unrelated messages or already complete session

    REQ:
    • session_id
    • any optional fields: property_type, booking_date, shift_type, min_price, max_price, max_occupancy

    RETURNS:
    ok {message asking for missing info OR instruction to call list_properties}
    err {error updating preferences}
    """
    db = SessionLocal()
    try:
        session_repo = SessionRepository()
        session = session_repo.get_by_id(db, session_id)
        
        if not session:
            return "Session not found. Please restart the conversation."
        
        # Track what was updated in this call
        updates = {}
        newly_set = []
        
        # Update property type
        if property_type:
            updates["property_type"] = property_type
            property_display = "farmhouse" if property_type == "farm" else "hut"
            newly_set.append(f"property type: **{property_display}**")
        
        # Update booking date
        if booking_date:
            try:
                date_obj = datetime.strptime(booking_date, "%Y-%m-%d")
                updates["booking_date"] = date_obj.date()
                formatted_date = date_obj.strftime("%d %B %Y (%A)")
                newly_set.append(f"date: **{formatted_date}**")
            except ValueError:
                return "❌ Invalid date format. Please use YYYY-MM-DD format."
        
        # Update shift type
        if shift_type:
            updates["shift_type"] = shift_type
            newly_set.append(f"shift: **{shift_type}**")
        
        # Update price range
        if min_price is not None:
            updates["min_price"] = min_price
            newly_set.append(f"minimum price: **Rs. {min_price}**")
        
        if max_price is not None:
            updates["max_price"] = max_price
            newly_set.append(f"maximum price: **Rs. {max_price}**")
        
        # Update occupancy
        if max_occupancy is not None:
            updates["max_occupancy"] = max_occupancy
            newly_set.append(f"guests: **{max_occupancy} people**")
        
        # Save updates to session
        if updates:
            session_service = SessionService(session_repo)
            session_service.update_session_data(db, session_id, **updates)
            
            # Refresh session to get updated values
            db.refresh(session)
        
        # Build response message
        if not newly_set:
            return "No preferences were updated. Please tell me what you're looking for."
        
        # Check what's still missing (required fields)
        missing = []
        
        current_property_type = session.property_type
        current_date = session.booking_date
        current_shift = session.shift_type
        
        if not current_property_type:
            missing.append("**property type** (hut or farmhouse)")
        
        if not current_date:
            missing.append("**date** of booking")
        
        if not current_shift:
            missing.append("**shift type** (Day, Night, or Full Day)")
        
        # Provide helpful next steps
        if missing:
            # Determine what property type to mention
            property_display = "farmhouses" if current_property_type == "farm" else "huts" if current_property_type == "hut" else "properties"
            
            response = f"📋 To show you available {property_display}, I need:\n"
            response += "\n".join([f"  • {item}" for item in missing])
            response += "\n\nPlease provide these details! 😊"
        else:
            # All required fields are set - ready to search
            property_display = "farmhouses" if current_property_type == "farm" else "huts"
            response = f"🎉 Perfect! I have all the details to search for {property_display}.\n"
            response += "Let me show you the available options..."
        
        return response
        
    except Exception as e:
        logger.error(f"Error in set_booking_preferences tool: {e}", exc_info=True)
        return "Error updating preferences. Please try again."
    finally:
        db.close()


# Export tools list
session_tools = [
    set_booking_preferences,
]

__all__ = [
    "set_booking_preferences",
    "session_tools",
]
