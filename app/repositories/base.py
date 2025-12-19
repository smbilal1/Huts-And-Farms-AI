"""
Base repository class providing common CRUD operations.

This module implements the repository pattern with generic CRUD methods
that can be extended by specific repository classes.
"""

from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.orm import Session


ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Base repository class with common CRUD operations.
    
    This class provides generic database operations that can be inherited
    by specific repository classes for different models.
    
    Attributes:
        model: The SQLAlchemy model class this repository operates on
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize the repository with a model class.
        
        Args:
            model: The SQLAlchemy model class
        """
        self.model = model
    
    def get_by_id(self, db: Session, id: Any) -> Optional[ModelType]:
        """
        Retrieve a single record by its ID.
        
        Args:
            db: Database session
            id: Primary key value
            
        Returns:
            Model instance if found, None otherwise
        """
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[ModelType]:
        """
        Retrieve all records with pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            
        Returns:
            List of model instances
        """
        return db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, db: Session, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record.
        
        Args:
            db: Database session
            obj_in: Dictionary of field values for the new record
            
        Returns:
            Created model instance
        """
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(
        self, 
        db: Session, 
        db_obj: ModelType, 
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """
        Update an existing record.
        
        Args:
            db: Database session
            db_obj: Existing model instance to update
            obj_in: Dictionary of field values to update
            
        Returns:
            Updated model instance
        """
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, id: Any) -> None:
        """
        Delete a record by its ID.
        
        Args:
            db: Database session
            id: Primary key value of the record to delete
        """
        obj = self.get_by_id(db, id)
        if obj:
            db.delete(obj)
            db.commit()
