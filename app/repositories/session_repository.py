"""
Session repository for managing user session data.

This module provides database operations for the Session model,
including session creation, retrieval, and updates.
"""

from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import and_

from app.repositories.base import BaseRepository
from app.models.user import Session


class SessionRepository(BaseRepository[Session]):
    """
    Repository for Session model operations.
    
    Provides methods for managing user sessions including creation,
    retrieval by user, session data updates, and cleanup of inactive sessions.
    """
    
    def __init__(self):
        """Initialize the SessionRepository with the Session model."""
        super().__init__(Session)
    
    def get_by_user_id(self, db: DBSession, user_id: str) -> Optional[Session]:
        """
        Retrieve a session by user ID.
        
        Args:
            db: Database session
            user_id: UUID of the user
            
        Returns:
            Session instance if found, None otherwise
        """
        return db.query(Session).filter(Session.user_id == user_id).first()
    
    def create_or_get(
        self, 
        db: DBSession, 
        user_id: str, 
        session_id: str,
        source: str = "Website"
    ) -> Session:
        """
        Get existing session or create a new one for a user.
        
        If a session already exists for the user, return it.
        Otherwise, create a new session with the provided session_id.
        
        Args:
            db: Database session
            user_id: UUID of the user
            session_id: Unique session identifier
            source: Source of the session ("Website" or "Chatbot")
            
        Returns:
            Existing or newly created Session instance
        """
        # Check if session already exists
        existing_session = self.get_by_user_id(db, user_id)
        
        if existing_session:
            return existing_session
        
        # Create new session
        session_data = {
            "id": session_id,
            "user_id": user_id,
            "source": source,
            "created_at": datetime.utcnow()
        }
        
        return self.create(db, session_data)
    
    def update_session_data(
        self,
        db: DBSession,
        session_id: str,
        **kwargs
    ) -> Optional[Session]:
        """
        Update session data fields.
        
        Accepts any session field as a keyword argument and updates
        the session with the provided values.
        
        Args:
            db: Database session
            session_id: Session ID to update
            **kwargs: Field names and values to update (e.g., booking_id="ABC-123")
            
        Returns:
            Updated Session instance if found, None otherwise
            
        Example:
            update_session_data(
                db, 
                "session-123",
                booking_id="John-2024-01-01-Day",
                property_id="prop-uuid",
                shift_type="Day"
            )
        """
        session = db.query(Session).filter(Session.id == session_id).first()
        
        if not session:
            return None
        
        # Update provided fields
        for field, value in kwargs.items():
            if hasattr(session, field):
                setattr(session, field, value)
        
        db.commit()
        db.refresh(session)
        return session
    
    def get_inactive_sessions(
        self,
        db: DBSession,
        inactive_days: int = 30
    ) -> List[Session]:
        """
        Retrieve sessions that have been inactive for a specified number of days.
        
        A session is considered inactive if it was created more than
        `inactive_days` ago.
        
        Args:
            db: Database session
            inactive_days: Number of days to consider a session inactive (default: 30)
            
        Returns:
            List of inactive Session instances
        """
        cutoff_date = datetime.utcnow() - timedelta(days=inactive_days)
        
        return (
            db.query(Session)
            .filter(Session.created_at < cutoff_date)
            .all()
        )
    
    def delete_session(self, db: DBSession, session_id: str) -> bool:
        """
        Delete a session by its ID.
        
        Args:
            db: Database session
            session_id: Session ID to delete
            
        Returns:
            True if session was deleted, False if not found
        """
        session = db.query(Session).filter(Session.id == session_id).first()
        
        if not session:
            return False
        
        db.delete(session)
        db.commit()
        return True
    
    def clear_session_data(
        self,
        db: DBSession,
        session_id: str
    ) -> Optional[Session]:
        """
        Clear/reset session booking data while keeping the session active.
        
        Resets booking-related fields to None while preserving the session
        and user association.
        
        Args:
            db: Database session
            session_id: Session ID to clear
            
        Returns:
            Updated Session instance if found, None otherwise
        """
        session = db.query(Session).filter(Session.id == session_id).first()
        
        if not session:
            return None
        
        # Reset booking-related fields
        session.booking_id = None
        session.property_id = None
        session.property_type = None
        session.booking_date = None
        session.shift_type = None
        session.min_price = None
        session.max_price = None
        session.max_occupancy = None
        
        db.commit()
        db.refresh(session)
        return session
