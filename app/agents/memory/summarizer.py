"""
Conversation Summarizer

Generates compressed summaries of conversation history using LLM.
Implements adaptive compression based on generation count.
Supports multiple LLM providers (OpenAI, Gemini) via configuration.
"""

from typing import Dict, List, Optional
from app.core.config import settings
from app.agents.llm_factory import get_llm_for_summary, OPENAI_CHAT_MODEL


def generate_summary(
    previous_summary: Optional[str],
    recent_messages: List[Dict[str, str]],
    session_state: Dict[str, any],
    generation_count: int = 0
) -> str:
    """
    Generate conversation summary with adaptive compression.
    
    Args:
        previous_summary: Existing summary (None for first generation)
        recent_messages: Recent messages to summarize
        session_state: Current session facts
        generation_count: How many times summary has been generated
        
    Returns:
        Updated summary text
    """
    
    # Determine compression level
    compression_instruction = _get_compression_instruction(generation_count)
    
    # Format messages for prompt
    messages_text = _format_messages(recent_messages)
    
    # Build prompt
    prompt = f"""You are a memory manager for a booking chatbot.

{compression_instruction}

Previous Summary:
{previous_summary or "None - this is the first summary"}

Recent Messages:
{messages_text}

Current Session State (source of truth):
- Property Type: {session_state.get('property_type') or 'Not set'}
- Booking Date: {session_state.get('booking_date') or 'Not set'}
- Shift Type: {session_state.get('shift_type') or 'Not set'}
- Property ID: {session_state.get('property_id') or 'Not selected'}
- Booking ID: {session_state.get('booking_id') or 'Not created'}

Generate updated summary (max 100 words, focus on user intent and decisions):
"""
    
    try:
        # Get LLM client based on provider
        provider = settings.LLM_PROVIDER.lower()
        
        if provider == "openai":
            client = get_llm_for_summary()
            response = client.chat.completions.create(
                model=OPENAI_CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0
            )
            summary = response.choices[0].message.content.strip()
            
        elif provider == "gemini":
            model = get_llm_for_summary()
            response = model.generate_content(prompt)
            summary = response.text.strip()
            
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        
        print(f"📝 Generated summary ({len(summary)} chars) using {provider.upper()}")
        return summary
        
    except Exception as e:
        print(f"❌ Summary generation failed: {e}")
        # Fallback: return previous summary or basic summary
        if previous_summary:
            return previous_summary
        return "Conversation in progress."


def _get_compression_instruction(generation_count: int) -> str:
    """
    Get compression instructions based on how many times summary has been generated.
    
    Args:
        generation_count: Number of times summary has been generated
        
    Returns:
        Instruction text for the summarizer
    """
    if generation_count == 0:
        # First summary - no previous context
        return """
Create a concise summary of the conversation.
Focus on:
- What the user wants (property type, date, shift)
- What properties were discussed
- Any decisions made
"""
    
    elif generation_count < 3:
        # Early summaries (2nd, 3rd) - preserve details
        return """
Update the previous summary with new information.
Keep all important details from previous summary.
Add new developments from recent messages.
Maintain chronological flow.
"""
    
    else:
        # Later summaries (4th+) - compress aggressively
        return """
Update the summary focusing on CURRENT STATE only.

From previous summary, keep ONLY:
- Core booking details (property name, date, shift)
- Current status (confirmed/pending/awaiting payment)

DROP from previous summary:
- Early exploration details
- Old property lists
- Resolved questions
- Minor interactions

Emphasize recent developments from new messages.
Be concise - compress old information.
"""


def _format_messages(messages: List[Dict[str, str]]) -> str:
    """
    Format messages for inclusion in prompt.
    
    Args:
        messages: List of message dicts
        
    Returns:
        Formatted string
    """
    if not messages:
        return "No recent messages"
    
    formatted = []
    for msg in messages:
        role = msg['role'].capitalize()
        content = msg['content'][:200]  # Truncate long messages
        formatted.append(f"{role}: {content}")
    
    return "\n".join(formatted)
