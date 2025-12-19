"""
Session service for business logic related to user sessions.

This module provides the SessionService class that implements all session-related
business logic including session creation, retrieval, updates, and cleanup.
"""

import logging
from typing import Dict, Optional, Any, Union
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.models.user import Session

logger = logging.getLogger(__name__)


class SessionService:
    """
    Service for managing user session operations.
    
    Handles all session-related business logic including session creation,
    retrieval, data updates, and session clearing.
    """
    
    def __init__(
        self,
        session_repo: Optional[SessionRepository] = None,
        user_repo: Optional[UserRepository] = None
    ):
        """
        Initialize the session service with repository dependencies.
        
        Args:
            session_repo: Repository for session operations
            user_repo: Repository for user operations
        """
        self.session_repo = session_repo or SessionRepository()
        self.user_repo = user_repo or UserRepository()
    
    def get_or_create_session(
        self,
        db: DBSession,
        user_id: Union[str, UUID],
        session_id: str,
        source: str = "Website"
    ) -> Dict[str, Any]:
        """
        Get existing session or create a new one for a user.
        
        This method:
        1. Validates that the user exists
        2. Retrieves existing session or creates a new one
        3. Returns session information
        
        Args:
            db: Database session
            user_id: User's unique identifier (string or UUID)
            session_id: Unique session identifier
            source: Source of the session ("Website" or "Chatbot")
            
        Returns:
            Dictionary containing:
                - success: Boolean indicating operation success
                - session: Session object if successful
                - session_id: Session ID
                - message: Success or error message
        """
        try:
            # Convert user_id to UUID if it's a string
            if isinstance(user_id, str):
                try:
                    user_id = UUID(user_id)
                except ValueError:
                    logger.warning(f"Invalid UUID format: {user_id}")
                    return {
                        "success": False,
                        "error": "Invalid user ID",
                        "message": "User ID must be a valid UUID"
                    }
            
            # Validate user exists
            user = self.user_repo.get_by_id(db, user_id)
            if not user:
                logger.warning(f"User not found: {user_id}")
                return {
                    "success": False,
                    "error": "User not found",
                    "message": "The specified user does not exist"
                }
            
            # Validate source
            if source not in ["Website", "Chatbot"]:
                logger.warning(f"Invalid session source: {source}")
                source = "Website"  # Default to Website
            
            # Get or create session
            session = self.session_repo.create_or_get(
                db=db,
                user_id=user_id,
                session_id=session_id,
                source=source
            )
            
            logger.info(f"Session retrieved/created for user {user_id}: {session.id}")
            
            return {
                "success": True,
                "session": session,
                "session_id": session.id,
                "message": "Session retrieved successfully"
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_or_create_session: {e}", exc_info=True)
            db.rollback()
            return {
                "success": False,
                "error": "Database error",
                "message": f"Failed to retrieve or create session: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error in get_or_create_session: {e}", exc_info=True)
            db.rollback()
            return {
                "success": False,
                "error": "Internal error",
                "message": f"An unexpected error occurred: {str(e)}"
            }
    
    def update_session_data(
        self,
        db: DBSession,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update session data fields.
        
        This method updates any session fields provided as keyword arguments.
        Common fields include: booking_id, property_id, property_type,
        booking_date, shift_type, min_price, max_price, max_occupancy.
        
        Args:
            db: Database session
            session_id: Session ID to update
            **kwargs: Field names and values to update
            
        Returns:
            Dictionary containing:
                - success: Boolean indicating operation success
                - session: Updated Session object if successful
                - message: Success or error message
                
        Example:
            update_session_data(
                db,
                "session-123",
                booking_id="John-2024-01-01-Day",
                property_id="prop-uuid",
                shift_type="Day"
            )
        """
        try:
            # Validate session exists
            existing_session = self.session_repo.get_by_id(db, session_id)
            if not existing_session:
                logger.warning(f"Session not found: {session_id}")
                return {
                    "success": False,
                    "error": "Session not found",
                    "message": f"No session found with ID: {session_id}"
                }
            
            # Convert property_id to UUID if it's a string
            if "property_id" in kwargs and kwargs["property_id"] is not None:
                if isinstance(kwargs["property_id"], str):
                    try:
                        kwargs["property_id"] = UUID(kwargs["property_id"])
                    except ValueError:
                        logger.warning(f"Invalid property UUID format: {kwargs['property_id']}")
                        return {
                            "success": False,
                            "error": "Invalid property ID",
                            "message": "Property ID must be a valid UUID"
                        }
            
            # Update session
            updated_session = self.session_repo.update_session_data(
                db=db,
                session_id=session_id,
                **kwargs
            )
            
            if not updated_session:
                logger.error(f"Failed to update session: {session_id}")
                return {
                    "success": False,
                    "error": "Update failed",
                    "message": "Failed to update session data"
                }
            
            logger.info(f"Session updated: {session_id} with fields: {list(kwargs.keys())}")
            
            return {
                "success": True,
                "session": updated_session,
                "message": "Session data updated successfully"
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in update_session_data: {e}", exc_info=True)
            db.rollback()
            return {
                "success": False,
                "error": "Database error",
                "message": f"Failed to update session: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error in update_session_data: {e}", exc_info=True)
            db.rollback()
            return {
                "success": False,
                "error": "Internal error",
                "message": f"An unexpected error occurred: {str(e)}"
            }
    
    def clear_session(
        self,
        db: DBSession,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Clear/reset session booking data while keeping the session active.
        
        This method resets all booking-related fields (booking_id, property_id,
        property_type, booking_date, shift_type, min_price, max_price, max_occupancy)
        to None while preserving the session and user association.
        
        Args:
            db: Database session
            session_id: Session ID to clear
            
        Returns:
            Dictionary containing:
                - success: Boolean indicating operation success
                - session: Cleared Session object if successful
                - message: Success or error message
        """
        try:
            # Validate session exists
            existing_session = self.session_repo.get_by_id(db, session_id)
            if not existing_session:
                logger.warning(f"Session not found: {session_id}")
                return {
                    "success": False,
                    "error": "Session not found",
                    "message": f"No session found with ID: {session_id}"
                }
            
            # Clear session data
            cleared_session = self.session_repo.clear_session_data(
                db=db,
                session_id=session_id
            )
            
            if not cleared_session:
                logger.error(f"Failed to clear session: {session_id}")
                return {
                    "success": False,
                    "error": "Clear failed",
                    "message": "Failed to clear session data"
                }
            
            logger.info(f"Session cleared: {session_id}")
            
            return {
                "success": True,
                "session": cleared_session,
                "message": "Session data cleared successfully"
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in clear_session: {e}", exc_info=True)
            db.rollback()
            return {
                "success": False,
                "error": "Database error",
                "message": f"Failed to clear session: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error in clear_session: {e}", exc_info=True)
            db.rollback()
            return {
                "success": False,
                "error": "Internal error",
                "message": f"An unexpected error occurred: {str(e)}"
            }
    
    def get_session_info(
        self,
        db: DBSession,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve session information.
        
        Args:
            db: Database session
            session_id: Session ID to retrieve
            
        Returns:
            Dictionary containing:
                - success: Boolean indicating operation success
                - session: Session object if successful
                - message: Success or error message
        """
        try:
            session = self.session_repo.get_by_id(db, session_id)
            
            if not session:
                logger.warning(f"Session not found: {session_id}")
                return {
                    "success": False,
                    "error": "Session not found",
                    "message": f"No session found with ID: {session_id}"
                }
            
            return {
                "success": True,
                "session": session,
                "message": "Session retrieved successfully"
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_session_info: {e}", exc_info=True)
            return {
                "success": False,
                "error": "Database error",
                "message": f"Failed to retrieve session: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error in get_session_info: {e}", exc_info=True)
            return {
                "success": False,
                "error": "Internal error",
                "message": f"An unexpected error occurred: {str(e)}"
            }
    
    def delete_session(
        self,
        db: DBSession,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Delete a session completely.
        
        Args:
            db: Database session
            session_id: Session ID to delete
            
        Returns:
            Dictionary containing:
                - success: Boolean indicating operation success
                - message: Success or error message
        """
        try:
            # Validate session exists
            existing_session = self.session_repo.get_by_id(db, session_id)
            if not existing_session:
                logger.warning(f"Session not found: {session_id}")
                return {
                    "success": False,
                    "error": "Session not found",
                    "message": f"No session found with ID: {session_id}"
                }
            
            # Delete session
            deleted = self.session_repo.delete_session(db, session_id)
            
            if not deleted:
                logger.error(f"Failed to delete session: {session_id}")
                return {
                    "success": False,
                    "error": "Delete failed",
                    "message": "Failed to delete session"
                }
            
            logger.info(f"Session deleted: {session_id}")
            
            return {
                "success": True,
                "message": "Session deleted successfully"
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in delete_session: {e}", exc_info=True)
            db.rollback()
            return {
                "success": False,
                "error": "Database error",
                "message": f"Failed to delete session: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error in delete_session: {e}", exc_info=True)
            db.rollback()
            return {
                "success": False,
                "error": "Internal error",
                "message": f"An unexpected error occurred: {str(e)}"
            }
