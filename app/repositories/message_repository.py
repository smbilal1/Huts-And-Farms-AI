"""
Message repository for database operations related to messages.

This module provides data access methods for message-related operations,
including retrieving user messages, chat history, and saving messages.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.repositories.base import BaseRepository
from app.models.message import Message


class MessageRepository(BaseRepository[Message]):
    """
    Repository for message-related database operations.
    
    Extends BaseRepository to provide message-specific query methods
    for managing chat messages and conversation history.
    """
    
    def __init__(self):
        """Initialize the message repository with the Message model."""
        super().__init__(Message)
    
    def get_user_messages(
        self,
        db: Session,
        user_id,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """
        Retrieve all messages for a specific user with pagination.
        
        Args:
            db: Database session
            user_id: User's unique identifier (UUID)
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            
        Returns:
            List of Message instances ordered by timestamp (oldest first)
        """
        return (
            db.query(Message)
            .filter(Message.user_id == user_id)
            .order_by(Message.timestamp.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_chat_history(
        self,
        db: Session,
        user_id,
        limit: int = 50,
        oldest_first: bool = True
    ) -> List[Message]:
        """
        Retrieve chat history for a user.
        
        This method retrieves the most recent messages and can optionally
        reverse the order to show oldest messages first (typical chat display).
        
        Args:
            db: Database session
            user_id: User's unique identifier (UUID)
            limit: Maximum number of messages to retrieve
            oldest_first: If True, returns oldest messages first; if False, newest first
            
        Returns:
            List of Message instances
        """
        # Query most recent messages first
        messages = (
            db.query(Message)
            .filter(Message.user_id == user_id)
            .order_by(desc(Message.timestamp))
            .limit(limit)
            .all()
        )
        
        # Reverse to show oldest first if requested
        if oldest_first:
            messages = list(reversed(messages))
        
        return messages
    
    def save_message(
        self,
        db: Session,
        user_id,
        sender: str,
        content: str,
        whatsapp_message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> Message:
        """
        Save a new message to the database.
        
        Args:
            db: Database session
            user_id: User's unique identifier (UUID)
            sender: Message sender type ("user", "bot", or "admin")
            content: Message content/text
            whatsapp_message_id: Optional WhatsApp message ID for tracking
            timestamp: Optional custom timestamp (defaults to current UTC time)
            
        Returns:
            Created Message instance
        """
        message_data = {
            "user_id": user_id,
            "sender": sender,
            "content": content,
            "whatsapp_message_id": whatsapp_message_id,
            "timestamp": timestamp or datetime.utcnow()
        }
        
        return self.create(db, message_data)
    
    def get_messages_by_sender(
        self,
        db: Session,
        user_id,
        sender: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """
        Retrieve messages for a user filtered by sender type.
        
        Args:
            db: Database session
            user_id: User's unique identifier (UUID)
            sender: Sender type to filter by ("user", "bot", or "admin")
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            
        Returns:
            List of Message instances filtered by sender
        """
        return (
            db.query(Message)
            .filter(
                Message.user_id == user_id,
                Message.sender == sender
            )
            .order_by(Message.timestamp.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_messages_by_whatsapp_id(
        self,
        db: Session,
        whatsapp_message_id: str
    ) -> Optional[Message]:
        """
        Retrieve a message by its WhatsApp message ID.
        
        Useful for preventing duplicate message processing.
        
        Args:
            db: Database session
            whatsapp_message_id: WhatsApp message identifier
            
        Returns:
            Message instance if found, None otherwise
        """
        return (
            db.query(Message)
            .filter(Message.whatsapp_message_id == whatsapp_message_id)
            .first()
        )
    
    def get_by_whatsapp_id(
        self,
        db: Session,
        whatsapp_message_id: str
    ) -> Optional[Message]:
        """
        Retrieve a message by its WhatsApp message ID (alias method).
        
        This is an alias for get_messages_by_whatsapp_id for convenience.
        
        Args:
            db: Database session
            whatsapp_message_id: WhatsApp message identifier
            
        Returns:
            Message instance if found, None otherwise
        """
        return self.get_messages_by_whatsapp_id(db, whatsapp_message_id)
    
    def get_messages_by_filter(
        self,
        db: Session,
        user_id,
        sender: Optional[str] = None,
        content_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[Message]:
        """
        Retrieve messages with optional filters.
        
        Args:
            db: Database session
            user_id: User's unique identifier (UUID)
            sender: Optional sender type to filter by ("user", "bot", or "admin")
            content_filter: Optional SQL LIKE pattern for content filtering
            limit: Maximum number of records to return
            
        Returns:
            List of Message instances matching the filters
        """
        query = db.query(Message).filter(Message.user_id == user_id)
        
        if sender:
            query = query.filter(Message.sender == sender)
        
        if content_filter:
            query = query.filter(Message.content.like(content_filter))
        
        return (
            query
            .order_by(desc(Message.timestamp))
            .limit(limit)
            .all()
        )
