"""
State Change Detector

Deterministically detects when summarization should be triggered.
Based on:
1. Message count threshold
2. Session flag (set by tools when state changes)

NOT based on LLM decisions or keyword matching.
"""

from typing import List, Dict
from app.models import Session


# Define which tools trigger state changes
STATE_CHANGING_TOOLS = {
    "get_property_id_from_name",  # Property selected
    "create_booking",              # Booking created
    "process_payment_screenshot",  # Payment processed
    "process_payment_details",     # Payment processed
}


def should_summarize(
    message_count: int,
    session: Session,
    recent_messages: List[Dict[str, str]]
) -> bool:
    """
    Determine if summarization should be triggered.
    
    Summarization is triggered when ANY of these conditions is true:
    1. Message count reaches multiples of 6 (6, 12, 18, 24, ...)
    2. needs_summarization flag is set (tool changed state)
    
    This is DETERMINISTIC - no LLM or keyword matching involved.
    
    Args:
        message_count: Number of messages in buffer
        session: Session object
        recent_messages: Recent message list (not used currently)
        
    Returns:
        True if summarization should be triggered
    """
    
    # Rule 1: Message count reaches interval (every 6 messages)
    # Trigger at 6, 12, 18, 24, etc. (but not at 0)
    if message_count > 0 and message_count % 6 == 0:
        print(f"  → Trigger: Message count ({message_count}) reached interval (multiple of 6)")
        return True
    
    # Rule 2: State change flag set by tool (independent of message count)
    if hasattr(session, 'needs_summarization') and session.needs_summarization:
        print(f"  → Trigger: State change flag set (independent of message count)")
        return True
    
    # No summarization needed
    return False


def mark_state_change(session_id: str, db) -> None:
    """
    Mark that a state change occurred (called by tools).
    
    This sets the needs_summarization flag on the session.
    
    Args:
        session_id: Session ID
        db: Database session
    """
    from app.repositories.session_repository import SessionRepository
    
    session_repo = SessionRepository()
    session = session_repo.get_by_id(db, session_id)
    
    if session:
        session.needs_summarization = True
        db.commit()
        print(f"🔔 State change marked for session {session_id}")


def detect_conversation_phase(session: Session) -> str:
    """
    Detect current phase of conversation for context.
    
    Phases:
    - initial: Just started
    - discovery: User exploring options
    - selection: Property selected, reviewing details
    - booking: Creating booking
    - payment: Handling payment
    - confirmed: Booking confirmed
    
    Args:
        session: Session object
        
    Returns:
        Phase name
    """
    # Check session state to determine phase
    if session.booking_id:
        # Has booking - check if confirmed
        # (You'd need to check booking status from DB)
        return "payment"
    
    if session.property_id:
        return "selection"
    
    if session.property_type or session.booking_date:
        return "discovery"
    
    return "initial"
