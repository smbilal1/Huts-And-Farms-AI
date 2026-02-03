"""
LangGraph State-Based Chat Memory

This module implements explicit memory management for the booking agent:
- Long-term: Conversation summary (compressed knowledge)
- Short-term: Recent 4 messages (immediate context)
- Session state: Facts from DB (source of truth)

NOT using LangChain memory classes.
"""

from app.agents.memory.memory_manager import prepare_memory, clear_memory, MemoryContext

__all__ = ["prepare_memory", "clear_memory", "MemoryContext"]
