"""
Gemini AI Integration Client

This module provides integration with Google's Gemini AI for:
- Payment screenshot analysis and information extraction
- Transaction verification
- Image content analysis
"""

import google.generativeai as genai
import requests
from PIL import Image
import io
import json
import logging
from typing import Dict, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Client for interacting with Google's Gemini AI API.
    
    Handles payment screenshot analysis, text extraction, and transaction
    information parsing using Gemini's vision capabilities.
    """
    
    def __init__(self):
        """Initialize Gemini client with API key from settings."""
        try:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("GeminiClient initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GeminiClient: {e}")
            raise
    
    def extract_payment_info(self, image_url: str) -> Dict:
        """
        Extract payment information from a screenshot image.
        
        Analyzes an image to determine if it's a payment screenshot and extracts
        transaction details such as transaction ID, amount, sender/receiver info,
        and payment method.
        
        Args:
            image_url: URL of the payment screenshot image
            
        Returns:
            Dict containing:
                - success: bool - Whether extraction was successful
                - is_payment_screenshot: bool - Whether image is a payment screenshot
                - confidence_score: float - Confidence level (0-1)
                - extracted_data: Dict - Extracted payment information
                - error: str - Error message if any
                
        Example:
            >>> client = GeminiClient()
            >>> result = client.extract_payment_info("https://example.com/payment.jpg")
            >>> if result["is_payment_screenshot"]:
            ...     print(f"Amount: {result['extracted_data']['amount']}")
        """
        try:
            # Download image from URL
            logger.info(f"Downloading image from URL: {image_url}")
            response = requests.get(image_url, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to download image: HTTP {response.status_code}")
                return {
                    "success": False,
                    "is_payment_screenshot": False,
                    "confidence_score": 0.0,
                    "error": f"Failed to download image: HTTP {response.status_code}"
                }
            
            # Load image using PIL
            image = Image.open(io.BytesIO(response.content))
            logger.info(f"Image loaded successfully: {image.size}")
            
            # Generate prompt and analyze image
            prompt = self._get_payment_extraction_prompt()
            logger.info("Sending image to Gemini for analysis")
            
            response = self.model.generate_content([prompt, image])
            response_text = response.text.strip()
            
            logger.debug(f"Gemini response: {response_text[:200]}...")
            
            # Parse response
            result = self._parse_payment_response(response_text)
            
            # Log results
            is_payment = result.get("is_payment_screenshot", False)
            confidence = result.get("confidence_score", 0.0)
            
            logger.info(
                f"Analysis complete - Is payment: {is_payment}, "
                f"Confidence: {confidence:.2f}"
            )
            
            if is_payment:
                extracted = result.get("extracted_data", {})
                logger.info(
                    f"Extracted: Amount={extracted.get('amount')}, "
                    f"Transaction ID={extracted.get('transaction_id')}, "
                    f"Method={extracted.get('payment_method')}"
                )
            
            return result
            
        except requests.RequestException as e:
            logger.error(f"Network error downloading image: {e}")
            return {
                "success": False,
                "is_payment_screenshot": False,
                "confidence_score": 0.0,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error extracting payment info: {e}", exc_info=True)
            return {
                "success": False,
                "is_payment_screenshot": False,
                "confidence_score": 0.0,
                "error": f"Failed to extract payment info: {str(e)}"
            }
    
    def _get_payment_extraction_prompt(self) -> str:
        """
        Generate the prompt for payment information extraction.
        
        Returns:
            str: Detailed prompt for Gemini to analyze payment screenshots
        """
        return """
        First, determine if this image is a payment/transaction screenshot from any payment app 
        (EasyPaisa, JazzCash, Bank apps, PayPal, etc.) or receipt. Look for indicators like:
        - Transaction IDs or reference numbers
        - Amount with currency symbols (Rs, PKR, $, etc.)
        - Payment app interfaces/logos
        - Transaction status messages
        - Sender/receiver information
        - Date/time stamps in transaction context
        
        Then, if it IS a payment screenshot, extract the following information:
        
        1. Transaction/Reference ID (any alphanumeric ID)
        2. Amount paid (look for numbers with Rs, PKR, or currency symbols)
        3. Sender name (person who made the payment)
        4. Sender phone number (if visible)
        5. Receiver name or account title
        6. Receiver phone number
        7. Date and time of transaction
        8. Payment method (EasyPaisa, JazzCash, Bank transfer, etc.)
        9. Transaction status (Success, Completed, etc.)
        
        Return the information in this exact JSON format:
        {
            "is_payment_screenshot": true or false,
            "confidence_score": 0.0 to 1.0 (how confident you are this is a payment screenshot),
            "transaction_id": "extracted transaction ID or null",
            "amount": "extracted amount number only or null",
            "sender_name": "sender name or null",
            "sender_phone": "sender phone or null",
            "receiver_name": "receiver name or null", 
            "receiver_phone": "receiver phone or null",
            "transaction_date": "date and time or null",
            "payment_method": "payment method or null",
            "status": "transaction status or null",
            "raw_text": "all visible text in the image"
        }
        
        If this is NOT a payment screenshot, set all payment fields to null and explain what type of image it is in raw_text.
        If you cannot find any information, set the field to null. Be precise and only extract what is clearly visible.
        """
    
    def _parse_payment_response(self, response_text: str) -> Dict:
        """
        Parse Gemini's response and extract structured payment data.
        
        Args:
            response_text: Raw text response from Gemini
            
        Returns:
            Dict: Structured payment information with standardized fields
        """
        try:
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                # Find JSON object boundaries
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end]
            
            # Parse JSON
            extracted_data = json.loads(json_text)
            
            # Validate and normalize data
            is_payment = extracted_data.get("is_payment_screenshot", False)
            confidence = float(extracted_data.get("confidence_score", 0.0))
            
            # Ensure confidence is between 0 and 1
            confidence = max(0.0, min(1.0, confidence))
            
            return {
                "success": True,
                "is_payment_screenshot": is_payment,
                "confidence_score": confidence,
                "extracted_data": extracted_data,
                "raw_response": response_text
            }
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON from Gemini response: {e}")
            
            # Return default structure if parsing fails
            return {
                "success": True,
                "is_payment_screenshot": False,
                "confidence_score": 0.0,
                "extracted_data": {
                    "is_payment_screenshot": False,
                    "confidence_score": 0.0,
                    "raw_text": response_text,
                    "transaction_id": None,
                    "amount": None,
                    "sender_name": None,
                    "sender_phone": None,
                    "receiver_name": None,
                    "receiver_phone": None,
                    "transaction_date": None,
                    "payment_method": None,
                    "status": None
                },
                "raw_response": response_text,
                "parse_error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}", exc_info=True)
            return {
                "success": False,
                "is_payment_screenshot": False,
                "confidence_score": 0.0,
                "error": f"Failed to parse response: {str(e)}",
                "raw_response": response_text
            }
    
    def is_valid_payment_screenshot(
        self,
        result: Dict,
        min_confidence: float = 0.7
    ) -> bool:
        """
        Validate if the extraction result represents a valid payment screenshot.
        
        Checks if the image is identified as a payment screenshot with sufficient
        confidence and contains required payment information.
        
        Args:
            result: Dict returned from extract_payment_info()
            min_confidence: Minimum confidence threshold (default: 0.7)
            
        Returns:
            bool: True if valid payment screenshot with good confidence
            
        Example:
            >>> result = await client.extract_payment_info(image_url)
            >>> if client.is_valid_payment_screenshot(result):
            ...     # Process payment
        """
        if not result.get("success", False):
            logger.debug("Validation failed: extraction was not successful")
            return False
        
        if not result.get("is_payment_screenshot", False):
            logger.debug("Validation failed: not identified as payment screenshot")
            return False
        
        # Check confidence threshold
        confidence = result.get("confidence_score", 0.0)
        if confidence < min_confidence:
            logger.debug(
                f"Validation failed: confidence {confidence:.2f} "
                f"below threshold {min_confidence}"
            )
            return False
        
        # Check if at least some key payment data is present
        extracted_data = result.get("extracted_data", {})
        has_amount = extracted_data.get("amount") is not None
        has_transaction_id = extracted_data.get("transaction_id") is not None
        has_payment_method = extracted_data.get("payment_method") is not None
        
        # Require at least amount or transaction ID
        if not (has_amount or has_transaction_id):
            logger.debug(
                "Validation failed: missing both amount and transaction ID"
            )
            return False
        
        logger.info("Payment screenshot validation passed")
        return True
