from datetime import datetime, timedelta
from sqlalchemy import and_, desc
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import logging
from app.chatbot.models import Session, Message, ImageSent, VideoSent, Booking
from app.database import SessionLocal
# Set up logging for scheduler
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

def cleanup_inactive_sessions() -> dict:
    """
    Delete sessions that haven't had user messages for 24+ hours.
    Also deletes related ImageSent and VideoSent records.
    
    Returns:
        dict: Summary of cleanup operation
    """
    db = SessionLocal()
    try:
        # Calculate cutoff time (24 hours ago)
        cutoff_time = datetime.utcnow() -  timedelta(hours=24)
        
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
            return {
                "success": True,
                "message": "No inactive sessions found",
                "deleted_sessions": 0,
                "deleted_image_records": 0,
                "deleted_video_records": 0
            }
        
        # Delete related ImageSent records
        deleted_image_records = db.query(ImageSent).filter(
            ImageSent.session_id.in_(inactive_session_ids)
        ).delete(synchronize_session=False)
        
        # Delete related VideoSent records  
        deleted_video_records = db.query(VideoSent).filter(
            VideoSent.session_id.in_(inactive_session_ids)
        ).delete(synchronize_session=False)
        
        # Delete the sessions
        deleted_sessions = db.query(Session).filter(
            Session.id.in_(inactive_session_ids)
        ).delete(synchronize_session=False)
        
        # Commit all deletions
        db.commit()
        
        return {
            "success": True,
            "message": f"Successfully cleaned up {deleted_sessions} inactive sessions",
            "deleted_sessions": deleted_sessions,
            "deleted_image_records": deleted_image_records,
            "deleted_video_records": deleted_video_records,
            "cutoff_time": cutoff_time.isoformat()
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error cleaning up inactive sessions: {e}")
        return {
            "success": False,
            "message": f"❌ Error cleaning up inactive sessions: {str(e)}"
        }
    finally:
        db.close()


def cleanup_inactive_sessions_for_user(user_id: str) -> dict:
    """
    Delete sessions for a specific user that haven't had user messages for 24+ hours.
    Also deletes related ImageSent and VideoSent records.
    
    Args:
        user_id: UUID string of the user
        
    Returns:
        dict: Summary of cleanup operation for the user
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
            return {
                "success": True,
                "message": f"No inactive sessions found for user {user_id}",
                "deleted_sessions": 0,
                "deleted_image_records": 0,
                "deleted_video_records": 0
            }
        
        # Delete related ImageSent records
        deleted_image_records = db.query(ImageSent).filter(
            ImageSent.session_id.in_(inactive_session_ids)
        ).delete(synchronize_session=False)
        
        # Delete related VideoSent records  
        deleted_video_records = db.query(VideoSent).filter(
            VideoSent.session_id.in_(inactive_session_ids)
        ).delete(synchronize_session=False)
        
        # Delete the sessions
        deleted_sessions = db.query(Session).filter(
            Session.id.in_(inactive_session_ids)
        ).delete(synchronize_session=False)
        
        # Commit all deletions
        db.commit()
        
        return {
            "success": True,
            "message": f"Successfully cleaned up {deleted_sessions} inactive sessions for user {user_id}",
            "deleted_sessions": deleted_sessions,
            "deleted_image_records": deleted_image_records,
            "deleted_video_records": deleted_video_records,
            "cutoff_time": cutoff_time.isoformat(),
            "user_id": user_id
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error cleaning up inactive sessions for user {user_id}: {e}")
        return {
            "success": False,
            "message": f"❌ Error cleaning up inactive sessions for user {user_id}: {str(e)}"
        }
    finally:
        db.close()


# Optional: Function to get inactive sessions without deleting (for preview)
def get_inactive_sessions_preview() -> dict:
    """
    Get a preview of sessions that would be deleted without actually deleting them.
    
    Returns:
        dict: Preview of sessions that would be affected
    """
    db = SessionLocal()
    try:
        # Calculate cutoff time (24 hours ago)
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
            
            # If no user message exists or last user message is older than 24 hours
            if not last_user_message or last_user_message.timestamp < cutoff_time:
                inactive_sessions.append({
                    "session_id": session.id,
                    "user_id": str(session.user_id),
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                    "last_user_message_time": last_user_message.timestamp.isoformat() if last_user_message else None,
                    "property_id": str(session.property_id) if session.property_id else None
                })
        
        return {
            "success": True,
            "message": f"Found {len(inactive_sessions)} inactive sessions",
            "inactive_sessions": inactive_sessions,
            "cutoff_time": cutoff_time.isoformat()
        }
        
    except Exception as e:
        print(f"Error getting inactive sessions preview: {e}")
        return {
            "success": False,
            "message": f"❌ Error getting inactive sessions preview: {str(e)}"
        }
    finally:
        db.close()


def expire_pending_bookings() -> dict:
    """
    Change status of bookings from 'Pending' to 'Expired' after 15 minutes.
    If a booking was created at 11:00, it will be marked as Expired at 11:16 if still pending.
    
    Returns:
        dict: Summary of expiration operation
    """
    db = SessionLocal()
    try:
        # Calculate cutoff time (15 minutes ago)
        cutoff_time = datetime.utcnow() - timedelta(minutes=15)
        
        # Find all pending bookings older than 15 minutes
        expired_bookings = db.query(Booking).filter(
            and_(
                Booking.status == "Pending",
                Booking.created_at < cutoff_time
            )
        ).all()
        
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
        
        # Update status to 'Expired' instead of deleting
        expired_count = db.query(Booking).filter(
            and_(
                Booking.status == "Pending",
                Booking.created_at < cutoff_time
            )
        ).update(
            {
                "status": "Expired",
                "updated_at": datetime.utcnow()
            },
            synchronize_session=False
        )
        
        # Commit the update
        db.commit()
        
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
        logger.error(f"❌ Error expiring pending bookings: {e}")
        return {
            "success": False,
            "message": f"❌ Error expiring pending bookings: {str(e)}"
        }
    finally:
        db.close()


# Scheduler function - you can call this with a cron job or scheduler
def scheduled_cleanup():
    """
    Function to be called by a scheduler (cron job, celery, etc.)
    Runs both session cleanup and booking expiration.
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


def start_cleanup_scheduler():
    """
    Start the background scheduler for session and booking cleanup.
    Runs cleanup every 15 minutes.
    """
    global scheduler
    
    if scheduler is not None and scheduler.running:
        logger.warning("Scheduler is already running")
        return
    
    try:
        scheduler = BackgroundScheduler()
        
        # Add job to run cleanup every 15 minutes
        scheduler.add_job(
            func=scheduled_cleanup,
            trigger="interval",
            minutes=15,
            id='cleanup_job',
            name='Session and Booking Cleanup Job',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("✅ Cleanup scheduler started - runs every 15 minutes")
        logger.info("   - Deletes inactive sessions (24+ hours)")
        logger.info("   - Expires pending bookings (15+ minutes) - Status changed to 'Expired'")
        
        # Ensure scheduler shuts down when the application exits
        atexit.register(stop_cleanup_scheduler)
        
    except Exception as e:
        logger.error(f"❌ Failed to start cleanup scheduler: {e}")
        raise


def stop_cleanup_scheduler():
    """
    Stop the background scheduler gracefully.
    """
    global scheduler
    
    if scheduler and scheduler.running:
        try:
            scheduler.shutdown(wait=True)
            logger.info("🛑 Cleanup scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")


def get_scheduler_status() -> dict:
    """
    Get the current status of the cleanup scheduler.
    
    Returns:
        dict: Scheduler status information
    """
    global scheduler
    
    if scheduler is None:
        return {
            "running": False,
            "message": "Scheduler not initialized"
        }
    
    jobs = []
    if scheduler.running:
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
    
    return {
        "running": scheduler.running if scheduler else False,
        "jobs": jobs,
        "message": "Scheduler is running" if scheduler and scheduler.running else "Scheduler is stopped"
    }


def get_expired_bookings_preview() -> dict:
    """
    Get a preview of pending bookings that would be deleted without actually deleting them.
    
    Returns:
        dict: Preview of bookings that would be affected
    """
    db = SessionLocal()
    try:
        # Calculate cutoff time (15 minutes ago)
        cutoff_time = datetime.utcnow() - timedelta(minutes=15)
        
        # Find all pending bookings older than 15 minutes
        expired_bookings = db.query(Booking).filter(
            and_(
                Booking.status == "Pending",
                Booking.created_at < cutoff_time
            )
        ).all()
        
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
        
        return {
            "success": True,
            "message": f"Found {len(booking_list)} expired pending bookings",
            "expired_bookings": booking_list,
            "cutoff_time": cutoff_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting expired bookings preview: {e}")
        return {
            "success": False,
            "message": f"❌ Error getting expired bookings preview: {str(e)}"
        }
    finally:
        db.close()


def run_cleanup_now() -> dict:
    """
    Run cleanup immediately (outside of scheduled time).
    
    Returns:
        dict: Cleanup result
    """
    logger.info("Manual cleanup triggered")
    return scheduled_cleanup()


def run_booking_expiration_now() -> dict:
    """
    Run booking expiration immediately (outside of scheduled time).
    Changes status from 'Pending' to 'Expired' for bookings older than 15 minutes.
    
    Returns:
        dict: Booking expiration result
    """
    logger.info("Manual booking expiration triggered")
    return expire_pending_bookings()


# Auto-start scheduler when module is imported (optional)
def auto_start_scheduler():
    """
    Automatically start the scheduler when this module is imported.
    Call this function in your main application startup.
    """
    try:
        start_cleanup_scheduler()
    except Exception as e:
        logger.error(f"Failed to auto-start scheduler: {e}")


# # Example usage in your main application:
# if __name__ == "__main__":
#     # Start the scheduler
#     start_cleanup_scheduler()
    
#     # Keep the main thread alive for demonstration
#     try:
#         import time
#         print("Scheduler is running. Press Ctrl+C to exit...")
#         while True:
#             time.sleep(60)  # Sleep for 1 minute
            
#     except KeyboardInterrupt:
#         print("\nShutting down...")
#         stop_cleanup_scheduler()