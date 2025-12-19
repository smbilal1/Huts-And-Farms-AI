"""
User repository for database operations related to users.

This module provides data access methods for user-related operations,
including CRUD operations and user lookup by various identifiers.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository[User]):
    """
    Repository for user-related database operations.
    
    Extends BaseRepository to provide user-specific query methods
    for managing users and looking them up by phone, email, or CNIC.
    """
    
    def __init__(self):
        """Initialize the user repository with the User model."""
        super().__init__(User)
    
    def get_by_id(self, db: Session, user_id) -> Optional[User]:
        """
        Retrieve a user by their user ID.
        
        Overrides base method to use user_id instead of id.
        
        Args:
            db: Database session
            user_id: User's unique identifier (UUID)
            
        Returns:
            User instance if found, None otherwise
        """
        return db.query(User).filter(User.user_id == user_id).first()
    
    def get_by_phone(self, db: Session, phone_number: str) -> Optional[User]:
        """
        Retrieve a user by their phone number.
        
        Args:
            db: Database session
            phone_number: User's phone number
            
        Returns:
            User instance if found, None otherwise
        """
        return db.query(User).filter(User.phone_number == phone_number).first()
    
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """
        Retrieve a user by their email address.
        
        Args:
            db: Database session
            email: User's email address
            
        Returns:
            User instance if found, None otherwise
        """
        return db.query(User).filter(User.email == email).first()
    
    def get_by_cnic(self, db: Session, cnic: str) -> Optional[User]:
        """
        Retrieve a user by their CNIC (national ID).
        
        Args:
            db: Database session
            cnic: User's CNIC number
            
        Returns:
            User instance if found, None otherwise
        """
        return db.query(User).filter(User.cnic == cnic).first()
    
    def create_or_get(
        self,
        db: Session,
        phone_number: str,
        **kwargs
    ) -> User:
        """
        Get an existing user by phone number or create a new one.
        
        This method first attempts to find a user by phone number.
        If not found, it creates a new user with the provided data.
        
        Args:
            db: Database session
            phone_number: User's phone number (required)
            **kwargs: Additional user fields (name, email, cnic, etc.)
            
        Returns:
            Existing or newly created User instance
        """
        # Try to get existing user
        user = self.get_by_phone(db, phone_number)
        
        if user:
            return user
        
        # Create new user if not found
        user_data = {"phone_number": phone_number, **kwargs}
        return self.create(db, user_data)
