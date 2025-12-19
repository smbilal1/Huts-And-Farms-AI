"""
Scheduler setup and management for background tasks.

This module handles the initialization, starting, stopping, and status
checking of the background scheduler for cleanup tasks.
"""

import logging
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from app.tasks.cleanup_tasks import scheduled_cleanup

# Set up logging for scheduler
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None





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
        logger.info("   - Deletes inactive sessions (6+ hours)")
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
        dict: Scheduler status information including running state and job details
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
    from app.tasks.cleanup_tasks import expire_pending_bookings
    
    logger.info("Manual booking expiration triggered")
    return expire_pending_bookings()


def auto_start_scheduler():
    """
    Automatically start the scheduler when this module is imported.
    Call this function in your main application startup.
    """
    try:
        start_cleanup_scheduler()
    except Exception as e:
        logger.error(f"Failed to auto-start scheduler: {e}")
