"""
Comprehensive tests for background tasks (cleanup tasks and scheduler).

This test suite verifies:
1. Cleanup tasks execute correctly
2. Booking expiration works
3. Scheduler lifecycle management
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.tasks.cleanup_tasks import (
    cleanup_inactive_sessions,
    expire_pending_bookings,
    scheduled_cleanup,
    get_inactive_sessions_preview,
    get_expired_bookings_preview,
    cleanup_inactive_sessions_for_user
)
from app.tasks.scheduler import (
    start_cleanup_scheduler,
    stop_cleanup_scheduler,
    get_scheduler_status,
    run_cleanup_now,
    run_booking_expiration_now
)
from app.models import Session as SessionModel, Message, Booking, ImageSent, VideoSent


class TestCleanupTasks:
    """Test suite for cleanup task functions."""
    
    @patch('app.tasks.cleanup_tasks.SessionLocal')
    def test_cleanup_inactive_sessions_no_sessions(self, mock_session_local):
        """Test cleanup when no inactive sessions exist."""
        # Setup mock
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.all.return_value = []
        
        # Execute
        result = cleanup_inactive_sessions()
        
        # Verify
        assert result["success"] is True
        assert result["deleted_sessions"] == 0
        assert "No inactive sessions found" in result["message"]
        mock_db.close.assert_called_once()
    
    @patch('app.tasks.cleanup_tasks.SessionLocal')
    def test_cleanup_inactive_sessions_with_old_sessions(self, mock_session_local):
        """Test cleanup successfully deletes inactive sessions."""
        # Setup mock database
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        # Create mock session with old message
        old_time = datetime.utcnow() - timedelta(hours=25)
        mock_session = Mock()
        mock_session.id = "session-1"
        mock_session.user_id = "user-1"
        
        mock_message = Mock()
        mock_message.timestamp = old_time
        
        # Setup query chain
        mock_db.query.return_value.all.return_value = [mock_session]
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_message
        mock_db.query.return_value.filter.return_value.delete.return_value = 1
        
        # Execute
        result = cleanup_inactive_sessions()
        
        # Verify
        assert result["success"] is True
        assert result["deleted_sessions"] == 1
        assert "cutoff_time" in result
        mock_db.commit.assert_called()
        mock_db.close.assert_called_once()
    
    @patch('app.tasks.cleanup_tasks.SessionLocal')
    def test_cleanup_inactive_sessions_handles_errors(self, mock_session_local):
        """Test cleanup handles database errors gracefully."""
        # Setup mock to raise exception
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        mock_db.query.side_effect = Exception("Database error")
        
        # Execute
        result = cleanup_inactive_sessions()
        
        # Verify
        assert result["success"] is False
        assert "Error" in result["message"]
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
    
    @patch('app.tasks.cleanup_tasks.SessionLocal')
    def test_cleanup_inactive_sessions_for_user(self, mock_session_local):
        """Test cleanup for specific user."""
        # Setup mock
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        old_time = datetime.utcnow() - timedelta(hours=25)
        mock_session = Mock()
        mock_session.id = "session-1"
        mock_session.user_id = "user-1"
        
        mock_message = Mock()
        mock_message.timestamp = old_time
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_session]
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_message
        mock_db.query.return_value.filter.return_value.delete.return_value = 1
        
        # Execute
        result = cleanup_inactive_sessions_for_user("user-1")
        
        # Verify
        assert result["success"] is True
        assert result["user_id"] == "user-1"
        assert result["deleted_sessions"] == 1
        mock_db.close.assert_called_once()
    
    @patch('app.tasks.cleanup_tasks.SessionLocal')
    @patch('app.tasks.cleanup_tasks.BookingRepository')
    def test_expire_pending_bookings_no_expired(self, mock_repo_class, mock_session_local):
        """Test booking expiration when no expired bookings exist."""
        # Setup mocks
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_expired_bookings.return_value = []
        
        # Execute
        result = expire_pending_bookings()
        
        # Verify
        assert result["success"] is True
        assert result["expired_bookings"] == 0
        assert "No expired pending bookings found" in result["message"]
        mock_db.close.assert_called_once()
    
    @patch('app.tasks.cleanup_tasks.SessionLocal')
    @patch('app.tasks.cleanup_tasks.BookingRepository')
    def test_expire_pending_bookings_with_expired(self, mock_repo_class, mock_session_local):
        """Test booking expiration successfully expires bookings."""
        # Setup mocks
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        # Create mock expired bookings
        mock_booking1 = Mock()
        mock_booking1.booking_id = "booking-1"
        mock_booking2 = Mock()
        mock_booking2.booking_id = "booking-2"
        
        mock_repo.get_expired_bookings.return_value = [mock_booking1, mock_booking2]
        mock_repo.update_status.return_value = Mock()
        
        # Execute
        result = expire_pending_bookings()
        
        # Verify
        assert result["success"] is True
        assert result["expired_bookings"] == 2
        assert "booking-1" in result["expired_booking_ids"]
        assert "booking-2" in result["expired_booking_ids"]
        assert mock_repo.update_status.call_count == 2
        mock_db.close.assert_called_once()
    
    @patch('app.tasks.cleanup_tasks.SessionLocal')
    @patch('app.tasks.cleanup_tasks.BookingRepository')
    def test_expire_pending_bookings_handles_errors(self, mock_repo_class, mock_session_local):
        """Test booking expiration handles errors gracefully."""
        # Setup mock to raise exception
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_expired_bookings.side_effect = Exception("Database error")
        
        # Execute
        result = expire_pending_bookings()
        
        # Verify
        assert result["success"] is False
        assert "Error" in result["message"]
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
    
    @patch('app.tasks.cleanup_tasks.cleanup_inactive_sessions')
    @patch('app.tasks.cleanup_tasks.expire_pending_bookings')
    def test_scheduled_cleanup(self, mock_expire, mock_cleanup):
        """Test scheduled cleanup runs both cleanup operations."""
        # Setup mocks
        mock_cleanup.return_value = {
            "success": True,
            "message": "Cleaned up 5 sessions",
            "deleted_sessions": 5
        }
        mock_expire.return_value = {
            "success": True,
            "message": "Expired 3 bookings",
            "expired_bookings": 3
        }
        
        # Execute
        result = scheduled_cleanup()
        
        # Verify
        assert "session_cleanup" in result
        assert "booking_expiration" in result
        assert result["session_cleanup"]["deleted_sessions"] == 5
        assert result["booking_expiration"]["expired_bookings"] == 3
        mock_cleanup.assert_called_once()
        mock_expire.assert_called_once()
    
    @patch('app.tasks.cleanup_tasks.SessionLocal')
    def test_get_inactive_sessions_preview(self, mock_session_local):
        """Test preview function returns session information."""
        # Setup mock
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        old_time = datetime.utcnow() - timedelta(hours=7)
        mock_session = Mock()
        mock_session.id = "session-1"
        mock_session.user_id = "user-1"
        mock_session.property_id = "property-1"
        mock_session.created_at = old_time
        
        mock_message = Mock()
        mock_message.timestamp = old_time
        
        mock_db.query.return_value.all.return_value = [mock_session]
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_message
        
        # Execute
        result = get_inactive_sessions_preview()
        
        # Verify
        assert result["success"] is True
        assert len(result["inactive_sessions"]) == 1
        assert result["inactive_sessions"][0]["session_id"] == "session-1"
        mock_db.close.assert_called_once()
    
    @patch('app.tasks.cleanup_tasks.SessionLocal')
    @patch('app.tasks.cleanup_tasks.BookingRepository')
    def test_get_expired_bookings_preview(self, mock_repo_class, mock_session_local):
        """Test preview function returns booking information."""
        # Setup mocks
        mock_db = Mock()
        mock_session_local.return_value = mock_db
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        old_time = datetime.utcnow() - timedelta(minutes=20)
        mock_booking = Mock()
        mock_booking.booking_id = "booking-1"
        mock_booking.user_id = "user-1"
        mock_booking.property_id = "property-1"
        mock_booking.booking_date = datetime.utcnow()
        mock_booking.created_at = old_time
        mock_booking.total_cost = 5000
        mock_booking.status = "Pending"
        
        mock_repo.get_expired_bookings.return_value = [mock_booking]
        
        # Execute
        result = get_expired_bookings_preview()
        
        # Verify
        assert result["success"] is True
        assert len(result["expired_bookings"]) == 1
        assert result["expired_bookings"][0]["booking_id"] == "booking-1"
        assert result["expired_bookings"][0]["status"] == "Pending"
        mock_db.close.assert_called_once()


class TestScheduler:
    """Test suite for scheduler lifecycle management."""
    
    def teardown_method(self):
        """Clean up scheduler after each test."""
        try:
            stop_cleanup_scheduler()
        except:
            pass
    
    @patch('app.tasks.scheduler.BackgroundScheduler')
    def test_start_cleanup_scheduler(self, mock_scheduler_class):
        """Test scheduler starts successfully."""
        # Setup mock
        mock_scheduler_instance = Mock()
        mock_scheduler_class.return_value = mock_scheduler_instance
        mock_scheduler_instance.running = False
        
        # Execute
        start_cleanup_scheduler()
        
        # Verify
        mock_scheduler_instance.add_job.assert_called_once()
        mock_scheduler_instance.start.assert_called_once()
        
        # Verify job configuration
        call_args = mock_scheduler_instance.add_job.call_args
        assert call_args[1]["trigger"] == "interval"
        assert call_args[1]["minutes"] == 15
        assert call_args[1]["id"] == "cleanup_job"
    
    @patch('app.tasks.scheduler.BackgroundScheduler')
    def test_start_cleanup_scheduler_already_running(self, mock_scheduler_class):
        """Test starting scheduler when already running."""
        # Setup mock
        mock_scheduler_instance = Mock()
        mock_scheduler_class.return_value = mock_scheduler_instance
        mock_scheduler_instance.running = True
        
        # Set global scheduler
        import app.tasks.scheduler as scheduler_module
        scheduler_module.scheduler = mock_scheduler_instance
        
        # Execute
        start_cleanup_scheduler()
        
        # Verify - should not start again
        mock_scheduler_instance.start.assert_not_called()
    
    @patch('app.tasks.scheduler.scheduler')
    def test_stop_cleanup_scheduler(self, mock_scheduler):
        """Test scheduler stops successfully."""
        # Setup mock
        mock_scheduler.running = True
        
        # Execute
        stop_cleanup_scheduler()
        
        # Verify
        mock_scheduler.shutdown.assert_called_once_with(wait=True)
    
    @patch('app.tasks.scheduler.scheduler')
    def test_stop_cleanup_scheduler_not_running(self, mock_scheduler):
        """Test stopping scheduler when not running."""
        # Setup mock
        mock_scheduler.running = False
        
        # Execute
        stop_cleanup_scheduler()
        
        # Verify - should not call shutdown
        mock_scheduler.shutdown.assert_not_called()
    
    def test_get_scheduler_status_not_initialized(self):
        """Test getting status when scheduler not initialized."""
        # Reset global scheduler
        import app.tasks.scheduler as scheduler_module
        original_scheduler = scheduler_module.scheduler
        scheduler_module.scheduler = None
        
        try:
            # Execute
            status = get_scheduler_status()
            
            # Verify
            assert status["running"] is False
            assert "not initialized" in status["message"].lower()
        finally:
            scheduler_module.scheduler = original_scheduler
    
    @patch('app.tasks.scheduler.scheduler')
    def test_get_scheduler_status_running(self, mock_scheduler):
        """Test getting status when scheduler is running."""
        # Setup mock
        mock_scheduler.running = True
        mock_job = Mock()
        mock_job.id = "cleanup_job"
        mock_job.name = "Cleanup Job"
        mock_job.next_run_time = datetime.utcnow()
        mock_job.trigger = "interval[0:15:00]"
        
        mock_scheduler.get_jobs.return_value = [mock_job]
        
        # Execute
        status = get_scheduler_status()
        
        # Verify
        assert status["running"] is True
        assert len(status["jobs"]) == 1
        assert status["jobs"][0]["id"] == "cleanup_job"
        assert "running" in status["message"].lower()
    
    @patch('app.tasks.scheduler.scheduled_cleanup')
    def test_run_cleanup_now(self, mock_cleanup):
        """Test manual cleanup execution."""
        # Setup mock
        mock_cleanup.return_value = {
            "session_cleanup": {"success": True},
            "booking_expiration": {"success": True}
        }
        
        # Execute
        result = run_cleanup_now()
        
        # Verify
        assert "session_cleanup" in result
        assert "booking_expiration" in result
        mock_cleanup.assert_called_once()
    
    @patch('app.tasks.cleanup_tasks.expire_pending_bookings')
    def test_run_booking_expiration_now(self, mock_expire):
        """Test manual booking expiration execution."""
        # Setup mock
        mock_expire.return_value = {
            "success": True,
            "expired_bookings": 2
        }
        
        # Execute
        result = run_booking_expiration_now()
        
        # Verify
        assert result["success"] is True
        assert result["expired_bookings"] == 2
        mock_expire.assert_called_once()


class TestSchedulerIntegration:
    """Integration tests for scheduler with cleanup tasks."""
    
    def teardown_method(self):
        """Clean up scheduler after each test."""
        import app.tasks.scheduler as scheduler_module
        scheduler_module.scheduler = None
    
    @patch('app.tasks.scheduler.BackgroundScheduler')
    @patch('app.tasks.cleanup_tasks.cleanup_inactive_sessions')
    @patch('app.tasks.cleanup_tasks.expire_pending_bookings')
    def test_scheduler_executes_cleanup_tasks(
        self, 
        mock_expire, 
        mock_cleanup, 
        mock_scheduler_class
    ):
        """Test that scheduler properly executes cleanup tasks."""
        # Reset global scheduler first
        import app.tasks.scheduler as scheduler_module
        scheduler_module.scheduler = None
        
        # Setup mocks
        mock_scheduler_instance = Mock()
        mock_scheduler_class.return_value = mock_scheduler_instance
        mock_scheduler_instance.running = False
        
        mock_cleanup.return_value = {"success": True, "deleted_sessions": 3}
        mock_expire.return_value = {"success": True, "expired_bookings": 2}
        
        # Start scheduler
        start_cleanup_scheduler()
        
        # Get the scheduled function
        call_args = mock_scheduler_instance.add_job.call_args
        scheduled_func = call_args[1]["func"]
        
        # Execute the scheduled function
        result = scheduled_func()
        
        # Verify both cleanup functions were called
        assert "session_cleanup" in result
        assert "booking_expiration" in result
        assert result["session_cleanup"]["deleted_sessions"] == 3
        assert result["booking_expiration"]["expired_bookings"] == 2


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
