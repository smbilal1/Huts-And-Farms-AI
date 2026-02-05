from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from pgvector.sqlalchemy import Vector
from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    # session_id = Column(String(64), ForeignKey("sessions.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    sender = Column(String(10))  # "user" or "bot"
    content = Column(Text)
    structured_response = Column(JSON, nullable=True)  # Store structured responses for frontend

    timestamp = Column(DateTime, default=datetime.utcnow)
    whatsapp_message_id = Column(String(100), nullable=True)

    query_embedding = Column(Vector(3072), nullable=True)  # use correct dimension
    user = relationship("User", backref="messages")



