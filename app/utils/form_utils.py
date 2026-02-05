"""
Form submission utility functions.

This module contains utilities for detecting and processing form submissions
in chat messages.
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime


def is_form_submission(message: str) -> bool:
    """
    Detect if a message is a form submission.
    
    Checks if message looks like comma-separated structured data:
    - "Farm, 2026-02-28, Full Night, 30"
    - "Hut, 2026-03-15, Day, 15, 5000, 10000"
    
    Args:
        message: User message to check
        
    Returns:
        True if message appears to be a form submission
    """
    if not message or not isinstance(message, str):
        return False
    
    # Split by comma and clean up
    parts = [part.strip() for part in message.split(',')]
    
    # Must have at least 2 parts and all parts must be non-empty
    if len(parts) < 2:
        return False
    
    # All parts must be non-empty
    if not all(part for part in parts):
        return False
    
    # Check for common form patterns
    # Pattern 1: Property type, date, shift, occupancy
    if len(parts) >= 3:
        property_type = parts[0].lower()
        date_part = parts[1]
        shift_part = parts[2]
        
        # Check if first part looks like property type
        if property_type in ['farm', 'hut', 'farmhouse']:
            # Check if second part looks like a date
            if is_date_like(date_part):
                # Check if third part looks like shift type
                if shift_part.lower() in ['day', 'night', 'full day', 'full night']:
                    return True
    
    # Pattern 2: Multiple comma-separated values that look structured
    # (at least 3 parts, some numeric values)
    if len(parts) >= 3:
        numeric_count = sum(1 for part in parts if is_numeric(part))
        if numeric_count >= 1:  # At least one numeric value
            return True
    
    return False


def is_date_like(text: str) -> bool:
    """
    Check if text looks like a date.
    
    Args:
        text: Text to check
        
    Returns:
        True if text appears to be a date
    """
    if not text:
        return False
    
    # Common date patterns
    date_patterns = [
        r'\d{4}-\d{2}-\d{2}',  # 2026-02-28
        r'\d{2}-\d{2}-\d{4}',  # 28-02-2026
        r'\d{2}/\d{2}/\d{4}',  # 28/02/2026
        r'\d{4}/\d{2}/\d{2}',  # 2026/02/28
    ]
    
    for pattern in date_patterns:
        if re.match(pattern, text.strip()):
            return True
    
    return False


def is_numeric(text: str) -> bool:
    """
    Check if text is numeric.
    
    Args:
        text: Text to check
        
    Returns:
        True if text is numeric
    """
    try:
        float(text.strip())
        return True
    except ValueError:
        return False


def parse_form_submission(message: str) -> Dict:
    """
    Parse a form submission message into structured data.
    
    Args:
        message: Form submission message
        
    Returns:
        Dictionary with parsed form data
    """
    if not is_form_submission(message):
        return {}
    
    parts = [part.strip() for part in message.split(',')]
    
    # Basic parsing - can be enhanced based on specific form structures
    form_data = {
        "raw_answers": parts,
        "submitted_at": datetime.utcnow().isoformat(),
        "answer_count": len(parts)
    }
    
    # Try to identify common fields
    if len(parts) >= 1:
        first_part = parts[0].lower()
        if first_part in ['farm', 'hut', 'farmhouse']:
            form_data["property_type"] = parts[0]
    
    if len(parts) >= 2 and is_date_like(parts[1]):
        form_data["booking_date"] = parts[1]
    
    if len(parts) >= 3:
        shift_part = parts[2].lower()
        if shift_part in ['day', 'night', 'full day', 'full night']:
            form_data["shift_type"] = parts[2]
    
    if len(parts) >= 4 and is_numeric(parts[3]):
        form_data["max_occupancy"] = parts[3]
    
    if len(parts) >= 5 and is_numeric(parts[4]):
        form_data["min_price"] = parts[4]
    
    if len(parts) >= 6 and is_numeric(parts[5]):
        form_data["max_price"] = parts[5]
    
    return form_data


def has_questions(structured_response: Optional[Dict]) -> bool:
    """
    Check if a structured response contains questions/forms.
    
    Args:
        structured_response: Structured response data
        
    Returns:
        True if response contains questions
    """
    if not structured_response or not isinstance(structured_response, dict):
        return False
    
    # Check for common question indicators
    response_type = structured_response.get("type", "")
    if response_type == "questions":
        return True
    
    # Check for questions array
    if "questions" in structured_response:
        return True
    
    # Check for form fields
    if "fields" in structured_response:
        return True
    
    return False


def mark_questions_as_submitted(
    structured_response: Dict,
    form_data: Dict
) -> Dict:
    """
    Mark questions in structured response as submitted with form data.
    
    Args:
        structured_response: Original structured response
        form_data: Form submission data
        
    Returns:
        Updated structured response with submission data
    """
    if not structured_response:
        return structured_response
    
    # Create a copy to avoid modifying original
    updated_response = structured_response.copy()
    
    # Add submission data
    updated_response["submitted"] = True
    updated_response["submitted_data"] = form_data
    updated_response["submitted_at"] = datetime.utcnow().isoformat()
    
    # If there are questions, mark them as answered
    if "questions" in updated_response:
        questions = updated_response["questions"]
        if isinstance(questions, list):
            for i, question in enumerate(questions):
                if isinstance(question, dict):
                    # Add answer if available
                    answers = form_data.get("raw_answers", [])
                    if i < len(answers):
                        question["answer"] = answers[i]
                    question["answered"] = True
    
    return updated_response


def create_form_questions_response(
    questions: List[str],
    form_id: Optional[str] = None,
    title: Optional[str] = None
) -> Dict:
    """
    Create a structured response for form questions.
    
    Args:
        questions: List of question strings
        form_id: Optional form identifier
        title: Optional form title
        
    Returns:
        Structured response dictionary
    """
    return {
        "type": "questions",
        "form_id": form_id or f"form_{datetime.utcnow().timestamp()}",
        "title": title or "Please provide the following information:",
        "questions": [
            {
                "id": i,
                "text": question,
                "answered": False,
                "answer": None
            }
            for i, question in enumerate(questions)
        ],
        "submitted": False,
        "created_at": datetime.utcnow().isoformat()
    }