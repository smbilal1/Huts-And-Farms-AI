"""
Form submission utility functions.

This module contains utilities for detecting and processing form submissions
in chat messages.
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime


def is_form_submission(message: str, previous_bot_message: Optional[str] = None) -> bool:
    """
    Detect if a message is a form submission.
    
    Detects various form submission patterns:
    - Multi-field: "Farm, 2026-02-28, Full Night, 30"
    - Two-field: "Aadil Raja, 4220180505531"
    - Single-field: "Yes", "4220180505531", "Aadil Raja"
    - Skip responses: "skip", "later", "no"
    - Email: "user@example.com"
    
    Args:
        message: User message to check
        previous_bot_message: Optional previous bot message for context
        
    Returns:
        True if message appears to be a form submission
    """
    if not message or not isinstance(message, str):
        return False
    
    message = message.strip()
    
    # First, check if it's clearly a conversational message
    if is_conversational_message(message):
        return False
    
    # Pattern 1: Comma-separated values (any count >= 2)
    if ',' in message:
        parts = [part.strip() for part in message.split(',')]
        # Must have at least 2 non-empty parts
        if len(parts) >= 2 and all(part for part in parts):
            return True
    
    # Pattern 2: Single confirmation words
    confirmation_words = ['yes', 'no', 'confirm', 'cancel', 'proceed', 'ok', 'okay']
    if message.lower() in confirmation_words:
        return True
    
    # Pattern 3: Skip/decline responses
    if is_skip_response(message):
        return True
    
    # Pattern 4: CNIC pattern (13 digits)
    if re.match(r'^\d{13}$', message):
        return True
    
    # Pattern 5: Phone number pattern
    if re.match(r'^\+?\d{10,15}$', message):
        return True
    
    # Pattern 6: Email pattern
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', message):
        return True
    
    # Pattern 7: Single name (2-4 words, alphabetic with spaces)
    # BUT exclude common polite phrases
    if re.match(r'^[A-Za-z\s]{2,50}$', message):
        words = message.split()
        if 2 <= len(words) <= 4:
            # Additional check: each word should be at least 2 chars
            # to avoid "ok", "hi", etc.
            if all(len(word) >= 2 for word in words):
                # Check if it's not a polite phrase
                if not is_conversational_message(message):
                    return True
    
    # Pattern 8: Date-like single value
    if is_date_like(message):
        return True
    
    # Pattern 9: Numeric value (could be occupancy, price, etc.)
    # But not too long (to avoid IDs or other numbers)
    if is_numeric(message) and 1 <= len(message) <= 10:
        return True
    
    # Pattern 10: Property type keywords
    if message.lower() in ['farm', 'hut', 'farmhouse']:
        return True
    
    # Pattern 11: Shift type keywords
    if message.lower() in ['day', 'night', 'full day', 'full night']:
        return True
    
    # Pattern 12: Address-like pattern (contains numbers and letters)
    # e.g., "123 Main Street", "House 45 Block B"
    if re.match(r'^[\w\s,.-]+\d+[\w\s,.-]*$', message) or re.match(r'^\d+[\w\s,.-]+$', message):
        # Check if it's not too long and not conversational
        if len(message) <= 100 and not is_conversational_message(message):
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


def is_conversational_message(message: str) -> bool:
    """
    Check if a message is conversational (not a form submission).
    
    Conversational messages typically:
    - Are questions
    - Contain multiple sentences
    - Have common conversational words
    - Are longer than typical form answers
    
    Args:
        message: Message to check
        
    Returns:
        True if message appears to be conversational
    """
    if not message:
        return False
    
    message = message.strip().lower()
    
    # Check for question marks
    if '?' in message:
        return True
    
    # Check for common conversational starters
    conversational_starters = [
        'i want', 'i need', 'can you', 'could you', 'please', 'help me',
        'show me', 'tell me', 'what is', 'how do', 'when can', 'where is',
        'i would like', 'looking for', 'interested in', 'mujhe', 'kya',
        'hello', 'hi', 'thanks', 'thank you', 'okay thanks', 'ok thanks'
    ]
    
    for starter in conversational_starters:
        if message.startswith(starter):
            return True
    
    # Check for multiple sentences (more than one period or exclamation)
    sentence_endings = message.count('.') + message.count('!')
    if sentence_endings > 1:
        return True
    
    # Check if message is too long for a form answer (more than 100 chars)
    if len(message) > 100:
        return True
    
    # Check for common conversational words
    conversational_words = ['please', 'want', 'need', 'like', 'would', 'could', 'should']
    word_count = sum(1 for word in conversational_words if word in message)
    if word_count >= 2:
        return True
    
    # Check for common polite phrases (2 words that are NOT names)
    polite_phrases = [
        'thank you', 'thanks', 'no thanks', 'ok thanks', 'okay thanks',
        'ok sure', 'okay sure', 'sure thing', 'sounds good', 'looks good',
        'got it', 'i see', 'makes sense', 'no problem', 'no worries',
        'all good', 'thats fine', 'thats ok', 'thats okay'
    ]
    
    if message in polite_phrases:
        return True
    
    return False


def is_skip_response(message: str) -> bool:
    """
    Check if message is a skip/decline response.
    
    Args:
        message: Message to check
        
    Returns:
        True if message is a skip response
    """
    if not message:
        return False
    
    message = message.strip().lower()
    
    skip_words = [
        'skip', 'pass', 'later', 'next', 'not now', 'maybe later',
        'dont have', "don't have", 'no cnic', 'no name', 'none',
        'na', 'n/a', 'not applicable'
    ]
    
    return message in skip_words or any(skip in message for skip in skip_words)


def parse_form_submission(message: str) -> Dict:
    """
    Parse a form submission message into structured data.
    
    Args:
        message: Form submission message
        
    Returns:
        Dictionary with parsed form data
    """
    if not message:
        return {}
    
    message = message.strip()
    
    # Initialize form data
    form_data = {
        "raw_message": message,
        "submitted_at": datetime.utcnow().isoformat(),
    }
    
    # Case 1: Comma-separated values
    if ',' in message:
        parts = [part.strip() for part in message.split(',')]
        form_data["raw_answers"] = parts
        form_data["answer_count"] = len(parts)
        
        # Try to identify fields based on patterns
        for i, part in enumerate(parts):
            # Property type
            if part.lower() in ['farm', 'hut', 'farmhouse']:
                form_data["property_type"] = part
            # Date
            elif is_date_like(part):
                form_data["booking_date"] = part
            # Shift type
            elif part.lower() in ['day', 'night', 'full day', 'full night']:
                form_data["shift_type"] = part
            # CNIC (13 digits)
            elif re.match(r'^\d{13}$', part):
                form_data["cnic"] = part
            # Phone number
            elif re.match(r'^\+?\d{10,15}$', part):
                form_data["phone"] = part
            # Email
            elif re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', part):
                form_data["email"] = part
            # Name (alphabetic with spaces)
            elif re.match(r'^[A-Za-z\s]{2,50}$', part):
                if "customer_name" not in form_data:
                    form_data["customer_name"] = part
            # Numeric values (could be occupancy, price)
            elif is_numeric(part):
                num_value = part
                # Try to determine what this number represents
                if "max_occupancy" not in form_data and int(float(part)) < 100:
                    form_data["max_occupancy"] = num_value
                elif "min_price" not in form_data:
                    form_data["min_price"] = num_value
                elif "max_price" not in form_data:
                    form_data["max_price"] = num_value
    
    # Case 2: Single value submissions
    else:
        form_data["raw_answers"] = [message]
        form_data["answer_count"] = 1
        
        # Check for skip/decline responses
        if is_skip_response(message):
            form_data["skipped"] = True
            form_data["skip_reason"] = message.lower()
        # Identify single value type
        elif message.lower() in ['yes', 'no', 'confirm', 'cancel', 'proceed', 'ok', 'okay']:
            form_data["confirmation"] = message.lower()
        elif re.match(r'^\d{13}$', message):
            form_data["cnic"] = message
        elif re.match(r'^\+?\d{10,15}$', message):
            form_data["phone"] = message
        elif re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', message):
            form_data["email"] = message
        elif re.match(r'^[A-Za-z\s]{2,50}$', message):
            words = message.split()
            if 2 <= len(words) <= 4 and all(len(word) >= 2 for word in words):
                form_data["customer_name"] = message
        elif is_date_like(message):
            form_data["booking_date"] = message
        elif message.lower() in ['farm', 'hut', 'farmhouse']:
            form_data["property_type"] = message
        elif message.lower() in ['day', 'night', 'full day', 'full night']:
            form_data["shift_type"] = message
        elif is_numeric(message):
            # Could be occupancy or price
            if int(float(message)) < 100:
                form_data["max_occupancy"] = message
            else:
                form_data["price"] = message
        # Address-like pattern
        elif re.match(r'^[\w\s,.-]+\d+[\w\s,.-]*$', message) or re.match(r'^\d+[\w\s,.-]+$', message):
            form_data["address"] = message
    
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