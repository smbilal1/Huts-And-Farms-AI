"""
Payment service for business logic related to payment processing.

This module provides the PaymentService class that implements all payment-related
business logic including payment screenshot processing, payment details verification,
and payment confirmation/rejection.
"""

import logging
import re
from typing import Dict, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.booking_repository import BookingRepository
from app.integrations.gemini import GeminiClient
from app.integrations.cloudinary import CloudinaryClient
from app.core.constants import EASYPAISA_NUMBER, EASYPAISA_ACCOUNT_HOLDER
from app.core.exceptions import PaymentException, IntegrationException

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Service for managing payment operations.
    
    Handles all payment-related business logic including payment screenshot
    analysis, payment details verification, and payment confirmation/rejection.
    """
    
    def __init__(
        self,
        booking_repo: Optional[BookingRepository] = None,
        gemini_client: Optional[GeminiClient] = None,
        cloudinary_client: Optional[CloudinaryClient] = None
    ):
        """
        Initialize the payment service with repository and client dependencies.
        
        Args:
            booking_repo: Repository for booking operations
            gemini_client: Client for AI-powered payment screenshot analysis
            cloudinary_client: Client for image upload operations
        """
        self.booking_repo = booking_repo or BookingRepository()
        self.gemini_client = gemini_client or GeminiClient()
        self.cloudinary_client = cloudinary_client or CloudinaryClient()
    
    async def process_payment_screenshot(
        self,
        db: Session,
        booking_id: str,
        image_data: str,
        is_base64: bool = True
    ) -> Dict[str, Any]:
        """
        Process payment screenshot for a booking.
        
        This method:
        1. Validates booking exists and is in correct state
        2. Uploads image to Cloudinary
        3. Analyzes image using Gemini AI to extract payment info
        4. Updates booking status to Waiting if valid payment screenshot
        5. Returns verification status and extracted payment information
        
        Args:
            db: Database session
            booking_id: Booking ID for payment
            image_data: Base64 encoded image or image URL
            is_base64: Whether image_data is base64 encoded (default: True)
        
        Returns:
            Dict containing:
                - success: bool - Whether processing was successful
                - message: str - Status message
                - payment_info: Dict - Extracted payment information
                - image_url: str - Uploaded image URL
                - error: str - Error message if failed
        
        Example:
            >>> service = PaymentService()
            >>> result = await service.process_payment_screenshot(
            ...     db=db,
            ...     booking_id="John-2024-12-25-Day",
            ...     image_data="base64_encoded_image_data"
            ... )
            >>> if result["success"]:
            ...     print(result["payment_info"])
        """
        try:
            # Get booking
            booking = self.booking_repo.get_by_booking_id(db, booking_id)
            
            if not booking:
                logger.warning(f"Booking not found: {booking_id}")
                return {
                    "success": False,
                    "error": "Booking not found"
                }
            
            # Check booking status
            if booking.status not in ["Pending", "Waiting"]:
                logger.warning(
                    f"Invalid booking status for payment: {booking_id} - {booking.status}"
                )
                return {
                    "success": False,
                    "error": f"Cannot process payment for booking with status: {booking.status}"
                }
            
            # Upload image to Cloudinary
            logger.info(f"Uploading payment screenshot for booking: {booking_id}")
            try:
                if is_base64:
                    image_url = await self.cloudinary_client.upload_base64(
                        image_data,
                        folder="payment_screenshots"
                    )
                else:
                    image_url = image_data
                
                logger.info(f"Image uploaded successfully: {image_url}")
            except Exception as e:
                logger.error(f"Failed to upload image: {e}", exc_info=True)
                raise IntegrationException(
                    message=f"Failed to upload image: {str(e)}",
                    code="CLOUDINARY_UPLOAD_FAILED"
                )
            
            # Analyze image using Gemini AI
            logger.info(f"Analyzing payment screenshot with Gemini AI")
            try:
                payment_info = self.gemini_client.extract_payment_info(image_url)
            except Exception as e:
                logger.error(f"Failed to analyze image: {e}", exc_info=True)
                raise IntegrationException(
                    message=f"Failed to analyze payment screenshot: {str(e)}",
                    code="GEMINI_ANALYSIS_FAILED"
                )
            
            # Check if it's a valid payment screenshot
            if not payment_info.get("success", False):
                logger.warning(f"Payment info extraction failed: {payment_info.get('error')}")
                return {
                    "success": False,
                    "error": "Failed to extract payment information from image",
                    "image_url": image_url,
                    "payment_info": payment_info
                }
            
            is_valid = self.gemini_client.is_valid_payment_screenshot(payment_info)
            
            if not is_valid:
                logger.warning(f"Invalid payment screenshot for booking: {booking_id}")
                return {
                    "success": False,
                    "error": "The uploaded image does not appear to be a valid payment screenshot. Please upload a clear payment confirmation screenshot.",
                    "image_url": image_url,
                    "payment_info": payment_info
                }
            
            # Update booking status to Waiting and store screenshot URL
            booking = self.booking_repo.update_status(db, booking_id, "Waiting")
            
            # Store the payment screenshot URL in the booking
            booking.payment_screenshot_url = image_url
            db.commit()
            
            logger.info(f"Booking status updated to Waiting and screenshot URL stored: {booking_id}")
            
            # Format success message
            message = self._format_screenshot_received_message(booking, payment_info)
            
            return {
                "success": True,
                "message": message,
                "payment_info": payment_info,
                "image_url": image_url,
                "booking_id": booking_id
            }
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error processing payment screenshot: {e}", exc_info=True)
            raise PaymentException(
                message="Database error occurred while processing payment",
                code="PAYMENT_SCREENSHOT_DB_ERROR"
            )
        except (PaymentException, IntegrationException):
            # Re-raise custom exceptions without wrapping
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing payment screenshot: {e}", exc_info=True)
            raise PaymentException(
                message="Failed to process payment screenshot. Please try again.",
                code="PAYMENT_SCREENSHOT_FAILED"
            )
    
    def process_payment_details(
        self,
        db: Session,
        booking_id: str,
        transaction_id: Optional[str] = None,
        sender_name: Optional[str] = None,
        amount: Optional[str] = None,
        sender_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process manual payment details when user provides transaction info via text.
        
        This method:
        1. Validates booking exists
        2. Validates and cleans payment details
        3. Checks for missing required fields
        4. Validates amount matches booking total
        5. Updates booking status to Waiting
        6. Returns verification status
        
        Args:
            db: Database session
            booking_id: Booking ID for payment
            transaction_id: Payment transaction/reference ID (optional)
            sender_name: Name of person who made payment (required)
            amount: Amount paid (required)
            sender_phone: Phone number of sender (optional)
        
        Returns:
            Dict containing:
                - success: bool - Whether processing was successful
                - message: str - Status message
                - payment_details: Dict - Processed payment details
                - missing_fields: List[str] - Missing required fields if any
                - error: str - Error message if failed
        
        Example:
            >>> service = PaymentService()
            >>> result = service.process_payment_details(
            ...     db=db,
            ...     booking_id="John-2024-12-25-Day",
            ...     sender_name="John Doe",
            ...     amount="5000",
            ...     transaction_id="TXN123456"
            ... )
        """
        try:
            # Get booking
            booking_id = booking_id.strip()
            booking = self.booking_repo.get_by_booking_id(db, booking_id)
            
            if not booking:
                logger.warning(f"Booking not found: {booking_id}")
                return {
                    "success": False,
                    "error": "❌ Booking not found. Please check your booking ID."
                }
            
            # Check booking status
            if booking.status not in ["Pending", "Waiting"]:
                logger.warning(
                    f"Invalid booking status for payment: {booking_id} - {booking.status}"
                )
                return {
                    "success": False,
                    "error": f"Cannot process payment for booking with status: {booking.status}"
                }
            
            # Clean and validate payment details
            payment_details = {
                'transaction_id': transaction_id,
                'sender_name': sender_name,
                'amount': amount,
                'sender_phone': sender_phone,
                'receiver_phone': EASYPAISA_NUMBER,
                'receiver_name': EASYPAISA_ACCOUNT_HOLDER
            }
            
            # Clean transaction ID
            if payment_details['transaction_id']:
                payment_details['transaction_id'] = re.sub(
                    r'[^A-Z0-9]', '', 
                    payment_details['transaction_id'].upper()
                )
            
            # Clean sender name
            if payment_details['sender_name']:
                payment_details['sender_name'] = payment_details['sender_name'].strip().title()
            
            # Check required fields
            required_fields = ['sender_name', 'amount']
            missing_fields = []
            
            for field in required_fields:
                if not payment_details.get(field) or len(str(payment_details[field]).strip()) < 2:
                    missing_fields.append(field)
            
            if missing_fields:
                missing_text = []
                if 'sender_name' in missing_fields:
                    missing_text.append("• Your full name (as it appears in payment) ✅ Required")
                if 'amount' in missing_fields:
                    missing_text.append("• Amount paid (e.g., 5000) ✅ Required")
                
                optional_text = "\n\n*Optional (if available):*\n• Transaction ID ⚪ Optional\n• Your phone number ⚪ Optional"
                
                return {
                    "success": False,
                    "message": f"""❌ *Missing Required Payment Information*

Please provide:
{chr(10).join(missing_text)}{optional_text}

Format example:
Name: John Doe  
Amount: {int(booking.total_cost)}
Transaction ID: TXN123456789 (optional)
Phone: 03001234567 (optional)""",
                    "missing_fields": missing_fields
                }
            
            # Validate amount
            try:
                provided_amount = float(re.sub(r'[^\d.]', '', str(payment_details['amount'])))
                expected_amount = float(booking.total_cost)
                
                if abs(provided_amount - expected_amount) > 1:
                    return {
                        "success": False,
                        "message": f"""❌ *Amount Mismatch*

Expected Amount: Rs. {int(expected_amount)}
Your Payment: Rs. {int(provided_amount)}

Please verify the amount and try again, or contact support if you believe this is correct."""
                    }
            except ValueError:
                return {
                    "success": False,
                    "message": "❌ Invalid amount format. Please provide amount in numbers only (e.g., 5000)"
                }
            
            # Update booking status to Waiting
            self.booking_repo.update_status(db, booking_id, "Waiting")
            logger.info(f"Booking status updated to Waiting: {booking_id}")
            
            # Format success message
            message = self._format_payment_details_received_message(
                booking,
                payment_details,
                provided_amount
            )
            
            return {
                "success": True,
                "message": message,
                "payment_details": payment_details,
                "status": "verification_pending"
            }
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error processing payment details: {e}", exc_info=True)
            raise PaymentException(
                message="❌ Database error occurred while processing payment details",
                code="PAYMENT_DETAILS_DB_ERROR"
            )
        except PaymentException:
            # Re-raise PaymentException without wrapping
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing payment details: {e}", exc_info=True)
            raise PaymentException(
                message="❌ Error processing payment details. Please try again or contact support.",
                code="PAYMENT_DETAILS_FAILED"
            )
    
    def verify_payment(
        self,
        db: Session,
        booking_id: str,
        verified_by: Optional[str] = None,
        verification_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify payment and confirm booking (admin use).
        
        This method is called by admin after manually verifying payment.
        Updates booking status from Waiting to Confirmed.
        
        Args:
            db: Database session
            booking_id: Booking ID to verify payment for
            verified_by: Optional identifier of admin who verified
            verification_notes: Optional notes about verification
        
        Returns:
            Dict containing:
                - success: bool - Whether verification was successful
                - message: str - Confirmation message
                - booking: Booking - Updated booking object
                - error: str - Error message if failed
        """
        try:
            # Get booking
            booking = self.booking_repo.get_by_booking_id(db, booking_id)
            
            if not booking:
                logger.warning(f"Booking not found: {booking_id}")
                return {
                    "success": False,
                    "error": "❌ Booking not found"
                }
            
            # Check if booking is in verifiable state
            if booking.status == "Confirmed":
                return {
                    "success": True,
                    "already_confirmed": True,
                    "message": "✅ Booking already confirmed",
                    "booking": booking
                }
            
            if booking.status not in ["Waiting", "Pending"]:
                return {
                    "success": False,
                    "error": f"Cannot verify payment for booking with status: {booking.status}"
                }
            
            # Update booking status to Confirmed
            booking = self.booking_repo.update_status(db, booking_id, "Confirmed")
            
            logger.info(
                f"Payment verified and booking confirmed: {booking_id} "
                f"(verified_by: {verified_by or 'system'})"
            )
            
            # Format confirmation message
            message = self._format_payment_confirmed_message(booking)
            
            return {
                "success": True,
                "message": message,
                "booking": booking,
                "customer_phone": booking.user.phone_number,
                "customer_user_id": booking.user.user_id
            }
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error verifying payment: {e}", exc_info=True)
            raise PaymentException(
                message="❌ Database error occurred while verifying payment",
                code="PAYMENT_VERIFY_DB_ERROR"
            )
        except PaymentException:
            # Re-raise PaymentException without wrapping
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error verifying payment: {e}", exc_info=True)
            raise PaymentException(
                message=f"❌ Error verifying payment: {str(e)}",
                code="PAYMENT_VERIFY_FAILED"
            )
    
    def reject_payment(
        self,
        db: Session,
        booking_id: str,
        reason: str,
        rejected_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reject payment after admin review (admin use).
        
        This method is called by admin when payment verification fails.
        Keeps booking status as Pending so user can retry payment.
        
        Args:
            db: Database session
            booking_id: Booking ID to reject payment for
            reason: Reason for rejection (required)
            rejected_by: Optional identifier of admin who rejected
        
        Returns:
            Dict containing:
                - success: bool - Whether rejection was processed
                - message: str - Rejection message for customer
                - booking: Booking - Booking object
                - error: str - Error message if failed
        """
        try:
            # Get booking
            booking = self.booking_repo.get_by_booking_id(db, booking_id)
            
            if not booking:
                logger.warning(f"Booking not found: {booking_id}")
                return {
                    "success": False,
                    "error": "❌ Booking not found"
                }
            
            # Ensure reason is provided
            if not reason or not reason.strip():
                return {
                    "success": False,
                    "error": "Rejection reason is required"
                }
            
            # Keep booking as Pending so user can retry
            if booking.status == "Waiting":
                booking = self.booking_repo.update_status(db, booking_id, "Pending")
            
            logger.info(
                f"Payment rejected for booking: {booking_id} "
                f"(reason: {reason}, rejected_by: {rejected_by or 'system'})"
            )
            
            # Format rejection message
            message = self._format_payment_rejected_message(booking, reason)
            
            return {
                "success": True,
                "message": message,
                "booking": booking,
                "booking_status": "Pending",
                "reason": reason,
                "customer_phone": booking.user.phone_number,
                "customer_user_id": booking.user.user_id
            }
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error rejecting payment: {e}", exc_info=True)
            raise PaymentException(
                message="❌ Database error occurred while rejecting payment",
                code="PAYMENT_REJECT_DB_ERROR"
            )
        except PaymentException:
            # Re-raise PaymentException without wrapping
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error rejecting payment: {e}", exc_info=True)
            raise PaymentException(
                message=f"❌ Error rejecting payment: {str(e)}",
                code="PAYMENT_REJECT_FAILED"
            )
    
    def get_payment_instructions(
        self,
        db: Session,
        booking_id: str
    ) -> Dict[str, Any]:
        """
        Get payment instructions for a pending booking.
        
        Args:
            db: Database session
            booking_id: Booking ID needing payment
        
        Returns:
            Dict containing:
                - success: bool - Whether retrieval was successful
                - message: str - Formatted payment instructions
                - amount: float - Amount to pay
                - easypaisa_number: str - Payment number
                - error: str - Error message if failed
        """
        try:
            # Get booking
            booking = self.booking_repo.get_by_booking_id(db, booking_id)
            
            if not booking:
                logger.warning(f"Booking not found: {booking_id}")
                return {
                    "success": False,
                    "error": "❌ Booking not found"
                }
            
            # Check if payment is needed
            if booking.status not in ["Pending", "Waiting"]:
                return {
                    "success": False,
                    "error": f"❌ This booking is {booking.status.lower()}. No payment needed."
                }
            
            # Format payment instructions
            message = f"""💳 *PAYMENT INSTRUCTIONS*

🆔 Booking ID: `{booking.booking_id}`
💰 Amount to Pay: *Rs. {int(booking.total_cost)}*

━━━━━━━━━━━━━━━━━━━━━━━━━

📱 *EasyPaisa Payment:*
Send Rs. {int(booking.total_cost)} to: *{EASYPAISA_NUMBER}*
Account Holder: *{EASYPAISA_ACCOUNT_HOLDER}*

📸 *After Payment:*
Send me:
1️⃣ Payment screenshot, OR
2️⃣ Payment details:
   • Your full name ✅ Required
   • Amount paid ✅ Required
   • Transaction ID ⚪ Optional
   • Your phone number ⚪ Optional

✅ We'll verify and confirm your booking within minutes!

_Ready when you are!_ 😊"""
            
            logger.info(f"Payment instructions provided for booking: {booking_id}")
            
            return {
                "success": True,
                "message": message,
                "amount": float(booking.total_cost),
                "easypaisa_number": EASYPAISA_NUMBER,
                "account_holder": EASYPAISA_ACCOUNT_HOLDER
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting payment instructions: {e}", exc_info=True)
            raise PaymentException(
                message="❌ Database error occurred",
                code="PAYMENT_INSTRUCTIONS_DB_ERROR"
            )
        except PaymentException:
            # Re-raise PaymentException without wrapping
            raise
        except Exception as e:
            logger.error(f"Error getting payment instructions: {e}", exc_info=True)
            raise PaymentException(
                message="❌ Failed to get payment instructions",
                code="PAYMENT_INSTRUCTIONS_FAILED"
            )
    
    def _format_screenshot_received_message(
        self,
        booking: Any,
        payment_info: Dict[str, Any]
    ) -> str:
        """
        Format message for payment screenshot received.
        
        Args:
            booking: Booking object
            payment_info: Extracted payment information
        
        Returns:
            str: Formatted message
        """
        extracted_data = payment_info.get("extracted_data", {})
        
        message = f"""📸 *Payment Screenshot Received!*

🆔 Booking ID: `{booking.booking_id}`
🏠 Property: *{booking.property.name}*
💰 Amount: Rs. {int(booking.total_cost)}

⏱️ *Verification Status:*
🔍 Under Review (Usually takes 5-10 minutes)
✅ You'll get confirmation message once verified

Thank you for your patience! 😊"""
        
        return message
    
    def _format_payment_details_received_message(
        self,
        booking: Any,
        payment_details: Dict[str, Any],
        provided_amount: float
    ) -> str:
        """
        Format message for payment details received.
        
        Args:
            booking: Booking object
            payment_details: Payment details dict
            provided_amount: Amount provided by user
        
        Returns:
            str: Formatted message
        """
        # Build submitted details message
        submitted_details = [
            f"👤 Sender: {payment_details['sender_name']}",
            f"💰 Amount: Rs. {int(provided_amount)}"
        ]
        
        if payment_details.get('transaction_id'):
            submitted_details.insert(0, f"🆔 Transaction ID: {payment_details['transaction_id']}")
        else:
            submitted_details.insert(0, "🆔 Transaction ID: Not provided (optional)")
        
        if payment_details.get('sender_phone'):
            submitted_details.append(f"📱 Phone: {payment_details['sender_phone']}")
        else:
            submitted_details.append("📱 Phone: Not provided (optional)")
        
        submitted_details.append(f"📞 EasyPaisa: {EASYPAISA_NUMBER}")
        
        message = f"""✅ *Payment Details Received*

Your payment is being verified by our team.

📋 *Details Submitted:*
{chr(10).join(submitted_details)}

⏱️ *Verification Status:*
🔍 Under Review (Usually takes 5-10 minutes)
✅ You'll get confirmation message once verified

Thank you for your patience! 😊

_Keep this conversation open to receive your confirmation._"""
        
        return message
    
    def _format_payment_confirmed_message(self, booking: Any) -> str:
        """
        Format message for payment confirmation.
        
        Args:
            booking: Confirmed booking object
        
        Returns:
            str: Formatted confirmation message
        """
        formatted_date = booking.booking_date.strftime("%d %B %Y (%A)")
        
        # Get property details
        property_name = booking.property.name
        property_address = getattr(booking.property, 'address', 'Address will be shared separately')
        property_contact = getattr(booking.property, 'contact_number', 'Contact details will be provided')
        
        message = f"""🎉 *BOOKING CONFIRMED!* ✅

Congratulations! Your payment has been verified and your booking is now confirmed!

📋 *Booking Details:*
🆔 Booking ID: `{booking.booking_id}`
🏠 Property: *{property_name}*
📍 Location: {property_address}
📅 Date: {formatted_date}
🕐 Shift: {booking.shift_type}
💰 Total Amount: Rs. {int(booking.total_cost)}

📞 *Property Contact:*
{property_contact}

🎊 *What's Next?*
• Save this confirmation message
• Arrive on time for your booking
• Contact property for any special requests
• Have a wonderful time!

Thank you for choosing us! 😊

_For any queries, feel free to message us._"""
        
        return message
    
    def _format_payment_rejected_message(
        self,
        booking: Any,
        reason: str
    ) -> str:
        """
        Format message for payment rejection.
        
        Args:
            booking: Booking object
            reason: Rejection reason
        
        Returns:
            str: Formatted rejection message
        """
        property_name = booking.property.name
        
        message = f"""❌ *PAYMENT VERIFICATION FAILED*

We couldn't verify your payment for:

📋 *Booking Details:*
🆔 Booking ID: `{booking.booking_id}`
🏠 Property: {property_name}
💰 Required Amount: Rs. {int(booking.total_cost)}

❌ *Issue Found:*
{reason}

━━━━━━━━━━━━━━━━━━━━━━━━━

💳 *TO COMPLETE YOUR BOOKING:*

1️⃣ *Make Correct Payment:*
   • Amount: Rs. {int(booking.total_cost)} (exact amount)
   • EasyPaisa: {EASYPAISA_NUMBER}
   • Account Name: {EASYPAISA_ACCOUNT_HOLDER}

2️⃣ *Send Payment Proof:*
   • Clear screenshot of payment confirmation
   • Or provide: Your Name ✅, Amount ✅, Transaction ID ⚪ (optional)

━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ *Your booking is still RESERVED for 30 minutes*

Need help? Contact our support team or try the payment again.

_We're here to help you complete your booking!_ 😊"""
        
        return message
