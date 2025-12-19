"""
DEPRECATED: This module is deprecated. Please use app.tasks.scheduler and app.tasks.cleanup_tasks instead.

This module is kept for backward compatibility only. All functionality has been moved to:
- app.tasks.scheduler: Scheduler setup and management
- app.tasks.cleanup_tasks: Cleanup task implementations

The functions in this module now delegate to the new modules.
"""

import logging

# Import from new locations
from app.tasks.scheduler import (
    start_cleanup_scheduler,
    stop_cleanup_scheduler,
    get_scheduler_status,
    run_cleanup_now,
    run_booking_expiration_now,
    auto_start_scheduler,
    scheduler
)

from app.tasks.cleanup_tasks import (
    cleanup_inactive_sessions,
    cleanup_inactive_sessions_for_user,
    get_inactive_sessions_preview,
    expire_pending_bookings,
    get_expired_bookings_preview,
    scheduled_cleanup
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Re-export all functions for backward compatibility
__all__ = [
    # Scheduler functions
    'start_cleanup_scheduler',
    'stop_cleanup_scheduler',
    'get_scheduler_status',
    'run_cleanup_now',
    'run_booking_expiration_now',
    'auto_start_scheduler',
    'scheduler',
    # Cleanup functions
    'cleanup_inactive_sessions',
    'cleanup_inactive_sessions_for_user',
    'get_inactive_sessions_preview',
    'expire_pending_bookings',
    'get_expired_bookings_preview',
    'scheduled_cleanup'
]
