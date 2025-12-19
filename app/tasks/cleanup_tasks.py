"""
Cleanup tasks for background processing.

This module contains cleanup functions for sessions and bookings that are
executed by the scheduler. These tasks use the service layer for business logic.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import and_, desc
from typing import Dict, Any

from app.database import SessionLocal
from app.models import Session, Message, Booking
from app.repositories.booking_repository import BookingRepository
from app.repositories.session_repository import SessionRepository

# Set up logging
logger = logging.getLogger(__name__)


def cleanup_inactive_sessions() -> Dict[str, Any]:
    """
    Delete sessions that haven't had user messages for 24+ hours.
    
    Returns:
        dict: Summary of cleanup operation including:
            - success: bool - Whether operation succeeded
            - message: str - Summary message
            - deleted_sessions: int - Number of sessions deleted
            - cutoff_time: str - ISO format cutoff timestamp
    """
    db = SessionLocal()
    try:
        # Calculate cutoff time (24 hours ago)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Get all sessions
        all_sessions = db.query(Session).all()
        
        inactive_session_ids = []
        
        for session in all_sessions:
            # Get the last user message for this session
            last_user_message = db.query(Message).filter(
                and_(
                    Message.user_id == session.user_id,
                    Message.sender == "user"
                )
            ).order_by(desc(Message.timestamp)).first()
            
            # If no user message exists or last user message is older than 24 hours
            if not last_user_message or last_user_message.timestamp < cutoff_time:
                inactive_session_ids.append(session.id)
        
        if not inactive_session_ids:
            logger.info("No inactive sessions found")
            return {
                "success": True,
                "message": "No inactive sessions found",
                "deleted_sessions": 0
            }
        
        # Delete the sessions
        deleted_sessions = db.query(Session).filter(
            Session.id.in_(inactive_session_ids)
        ).delete(synchronize_session=False)
        
        # Commit all deletions
        db.commit()
        
        logger.info(f"Successfully cleaned up {deleted_sessions} inactive sessions")
        
        return {
            "success": True,
            "message": f"Successfully cleaned up {deleted_sessions} inactive sessions",
            "deleted_sessions": deleted_sessions,
            "cutoff_time": cutoff_time.isoformat()
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning up inactive sessions: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Error cleaning up inactive sessions: {str(e)}"
        }
    finally:
        db.close()


def cleanup_inactive_sessions_for_user(user_id: str) -> Dict[str, Any]:
    """
    Delete sessions for a specific user that haven't had user messages for 24+ hours.
    
    Args:
        user_id: UUID string of the user
        
    Returns:
        dict: Summary of cleanup operation for the user including:
            - success: bool - Whether operation succeeded
            - message: str - Summary message
            - deleted_sessions: int - Number of sessions deleted
            - cutoff_time: str - ISO format cutoff timestamp
            - user_id: str - User ID that was cleaned up
    """
    db = SessionLocal()
    try:
        # Calculate cutoff time (24 hours ago)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Get all sessions for this user
        user_sessions = db.query(Session).filter(Session.user_id == user_id).all()
        
        inactive_session_ids = []
        
        for session in user_sessions:
            # Get the last user message for this session
            last_user_message = db.query(Message).filter(
                and_(
                    Message.user_id == session.user_id,
                    Message.sender == "user"
                )
            ).order_by(desc(Message.timestamp)).first()
            
            # If no user message exists or last user message is older than 24 hours
            if not last_user_message or last_user_message.timestamp < cutoff_time:
                inactive_session_ids.append(session.id)
        
        if not inactive_session_ids:
            logger.info(f"No inactive sessions found for user {user_id}")
            return {
                "success": True,
                "message": f"No inactive sessions found for user {user_id}",
                "deleted_sessions": 0
            }
        
        # Delete the sessions
        deleted_sessions = db.query(Session).filter(
            Session.id.in_(inactive_session_ids)
        ).delete(synchronize_session=False)
        
        # Commit all deletions
        db.commit()
        
        logger.info(f"Successfully cleaned up {deleted_sessions} inactive sessions for user {user_id}")
        
        return {
            "success": True,
            "message": f"Successfully cleaned up {deleted_sessions} inactive sessions for user {user_id}",
            "deleted_sessions": deleted_sessions,
            "cutoff_time": cutoff_time.isoformat(),
            "user_id": user_id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning up inactive sessions for user {user_id}: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Error cleaning up inactive sessions for user {user_id}: {str(e)}"
        }
    finally:
        db.close()


def get_inactive_sessions_preview() -> Dict[str, Any]:
    """
    Get a preview of sessions that would be deleted without actually deleting them.
    
    Returns:
        dict: Preview of sessions that would be affected including:
            - success: bool - Whether operation succeeded
            - message: str - Summary message
            - inactive_sessions: list - List of session info dicts
            - cutoff_time: str - ISO format cutoff timestamp
    """
    db = SessionLocal()
    try:
        # Calculate cutoff time (6 hours ago for preview)
        cutoff_time = datetime.utcnow() - timedelta(hours=6)
        
        # Get all sessions
        all_sessions = db.query(Session).all()
        
        inactive_sessions = []
        
        for session in all_sessions:
            # Get the last user message for this session
            last_user_message = db.query(Message).filter(
                and_(
                    Message.user_id == session.user_id,
                    Message.sender == "user"
                )
            ).order_by(desc(Message.timestamp)).first()
            
            # If no user message exists or last user message is older than cutoff
            if not last_user_message or last_user_message.timestamp < cutoff_time:
                inactive_sessions.append({
                    "session_id": session.id,
                    "user_id": str(session.user_id),
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                    "last_user_message_time": last_user_message.timestamp.isoformat() if last_user_message else None,
                    "property_id": str(session.property_id) if session.property_id else None
                })
        
        logger.info(f"Found {len(inactive_sessions)} inactive sessions in preview")
        
        return {
            "success": True,
            "message": f"Found {len(inactive_sessions)} inactive sessions",
            "inactive_sessions": inactive_sessions,
            "cutoff_time": cutoff_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting inactive sessions preview: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Error getting inactive sessions preview: {str(e)}"
        }
    finally:
        db.close()


def expire_pending_bookings() -> Dict[str, Any]:
    """
    Change status of bookings from 'Pending' to 'Expired' after 15 minutes.
    
    Uses the booking repository to find and update expired bookings.
    If a booking was created at 11:00, it will be marked as Expired at 11:16 
    if still pending.
    
    Returns:
        dict: Summary of expiration operation including:
            - success: bool - Whether operation succeeded
            - message: str - Summary message
            - expired_bookings: int - Number of bookings expired
            - expired_booking_ids: list - List of expired booking IDs
            - cutoff_time: str - ISO format cutoff timestamp
    """
    db = SessionLocal()
    booking_repo = BookingRepository()
    
    try:
        # Calculate cutoff time (15 minutes ago)
        cutoff_time = datetime.utcnow() - timedelta(minutes=15)
        
        # Find all pending bookings older than 15 minutes using repository
        expired_bookings = booking_repo.get_expired_bookings(db, expiration_minutes=15)
        
        if not expired_bookings:
            logger.info("No expired pending bookings found")
            return {
                "success": True,
                "message": "No expired pending bookings found",
                "expired_bookings": 0,
                "cutoff_time": cutoff_time.isoformat()
            }
        
        # Collect booking IDs for logging
        expired_booking_ids = [booking.booking_id for booking in expired_bookings]
        
        # Update each booking status to 'Expired' using repository
        expired_count = 0
        for booking in expired_bookings:
            updated_booking = booking_repo.update_status(db, booking.booking_id, "Expired")
            if updated_booking:
                expired_count += 1
        
        logger.info(f"✅ Marked {expired_count} bookings as Expired: {expired_booking_ids}")
        
        return {
            "success": True,
            "message": f"Successfully marked {expired_count} bookings as Expired",
            "expired_bookings": expired_count,
            "expired_booking_ids": expired_booking_ids,
            "cutoff_time": cutoff_time.isoformat()
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error expiring pending bookings: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Error expiring pending bookings: {str(e)}"
        }
    finally:
        db.close()


def get_expired_bookings_preview() -> Dict[str, Any]:
    """
    Get a preview of pending bookings that would be expired without actually expiring them.
    
    Returns:
        dict: Preview of bookings that would be affected including:
            - success: bool - Whether operation succeeded
            - message: str - Summary message
            - expired_bookings: list - List of booking info dicts
            - cutoff_time: str - ISO format cutoff timestamp
    """
    db = SessionLocal()
    booking_repo = BookingRepository()
    
    try:
        # Calculate cutoff time (15 minutes ago)
        cutoff_time = datetime.utcnow() - timedelta(minutes=15)
        
        # Find all pending bookings older than 15 minutes using repository
        expired_bookings = booking_repo.get_expired_bookings(db, expiration_minutes=15)
        
        booking_list = []
        for booking in expired_bookings:
            booking_list.append({
                "booking_id": booking.booking_id,
                "user_id": str(booking.user_id),
                "property_id": str(booking.property_id),
                "booking_date": booking.booking_date.isoformat() if booking.booking_date else None,
                "created_at": booking.created_at.isoformat() if booking.created_at else None,
                "minutes_old": int((datetime.utcnow() - booking.created_at).total_seconds() / 60) if booking.created_at else None,
                "total_cost": float(booking.total_cost) if booking.total_cost else None,
                "status": booking.status
            })
        
        logger.info(f"Found {len(booking_list)} expired pending bookings in preview")
        
        return {
            "success": True,
            "message": f"Found {len(booking_list)} expired pending bookings",
            "expired_bookings": booking_list,
            "cutoff_time": cutoff_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting expired bookings preview: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"❌ Error getting expired bookings preview: {str(e)}"
        }
    finally:
        db.close()


def scheduled_cleanup() -> Dict[str, Any]:
    """
    Function to be called by the scheduler.
    Runs both session cleanup and booking expiration.
    
    This is the main entry point for scheduled cleanup operations.
    It orchestrates both session and booking cleanup tasks.
    
    Returns:
        dict: Combined results from both cleanup operations including:
            - session_cleanup: dict - Results from session cleanup
            - booking_expiration: dict - Results from booking expiration
    """
    logger.info(f"Starting scheduled cleanup at {datetime.utcnow()}")
    
    # Clean up inactive sessions
    session_result = cleanup_inactive_sessions()
    logger.info(f"Session cleanup result: {session_result}")
    
    # Expire pending bookings (change status to Expired)
    booking_result = expire_pending_bookings()
    logger.info(f"Booking expiration result: {booking_result}")
    
    return {
        "session_cleanup": session_result,
        "booking_expiration": booking_result
    }
