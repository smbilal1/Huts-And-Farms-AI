"""
Notification service for sending booking-related notifications.

This module provides a service for sending notifications to customers and admins
through WhatsApp or web chat, handling payment confirmations, booking status updates,
and admin verification requests.
"""

from typing import Dict, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.integrations.whatsapp import WhatsAppClient
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.core.constants import EASYPAISA_NUMBER, VERIFICATION_WHATSAPP, WEB_ADMIN_USER_ID


class NotificationService:
    """
    Service for managing booking-related notifications.
    
    Handles sending notifications to customers and admins through appropriate
    channels (WhatsApp or web chat) based on the booking source.
    """
    
    def __init__(
        self,
        whatsapp_client: WhatsAppClient,
        message_repo: MessageRepository,
        session_repo: SessionRepository
    ):
        """
        Initialize the notification service.
        
        Args:
            whatsapp_client: Client for sending WhatsApp messages
            message_repo: Repository for saving messages to database
            session_repo: Repository for session operations
        """
        self.whatsapp_client = whatsapp_client
        self.message_repo = message_repo
        self.session_repo = session_repo
    
    async def notify_admin_payment_received(
        self,
        db: Session,
        booking: Any,
        payment_details: Dict[str, Any],
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Notify admin that payment has been received for verification.
        
        Sends a verification request to the admin with booking and payment details.
        Routes to WhatsApp admin or web admin based on configuration.
        
        Args:
            db: Database session
            booking: Booking instance with related user and property
            payment_details: Dict containing payment information:
                - transaction_id (optional): Payment transaction ID
                - amount: Amount paid
                - sender_name: Name of person who made payment
                - sender_phone (optional): Phone number of sender
            image_url: Optional URL of payment screenshot
            
        Returns:
            Dict containing:
                - success (bool): Whether notification was sent
                - message (str): Status message
                - error (str): Error message if failed
        """
        try:
            # Build payment details section
            payment_info = []
            if payment_details.get('transaction_id'):
                payment_info.append(f"🆔 Transaction ID: {payment_details['transaction_id']}")
            else:
                payment_info.append("🆔 Transaction ID: Not provided (optional)")
            
            payment_info.append(f"💵 Amount Claimed: Rs. {payment_details.get('amount', 'Not provided')}")
            payment_info.append(f"👤 Sender Name: {payment_details.get('sender_name', 'Not provided')}")
            
            if payment_details.get('sender_phone'):
                payment_info.append(f"📱 Sender Phone: {payment_details['sender_phone']}")
            else:
                payment_info.append("📱 Sender Phone: Not provided (optional)")
            
            payment_info.append(f"📞 Expected Receiver: {EASYPAISA_NUMBER}")
            
            # Format booking date
            booking_date_str = booking.booking_date.strftime("%d %B %Y")
            
            # Build verification message
            message = f"""🔔 *PAYMENT VERIFICATION REQUEST*

📋 *Booking Details:*
🆔 Booking ID: `{booking.booking_id}`
🏠 Property: {booking.property.name}
📅 Date: {booking_date_str}
🕐 Shift: {booking.shift_type}
💰 Expected Amount: Rs. {int(booking.total_cost)}
👤 Customer Name: {booking.user.name or 'Not provided'}
📱 Customer Phone: {booking.user.phone_number or 'Web User'}

💳 *Payment Details Provided:*
{chr(10).join(payment_info)}

✅ To CONFIRM: Reply `confirm {booking.booking_id}`
❌ To REJECT: Reply `reject {booking.booking_id} [reason]`

*Common Rejection Reasons:*
• amount_mismatch - Wrong amount paid
• transaction_not_found - Can't verify transaction
• insufficient_amount - Amount less than required
• incorrect_receiver - Wrong EasyPaisa number
• duplicate_transaction - Transaction already used
• invalid_details - Details don't match

Examples:
• `confirm {booking.booking_id}`
• `reject {booking.booking_id} amount_mismatch`
• `reject {booking.booking_id} insufficient_amount`"""
            
            # Determine routing: check if we have a web admin or WhatsApp admin
            # Try web admin first (if configured)
            if WEB_ADMIN_USER_ID:
                result = await self._send_to_web_admin(db, message)
                if result["success"]:
                    return result
            
            # Fall back to WhatsApp admin
            if VERIFICATION_WHATSAPP:
                result = await self._send_to_whatsapp_admin(db, message)
                return result
            
            return {
                "success": False,
                "error": "No admin notification channel configured"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to notify admin: {str(e)}"
            }
    
    async def notify_customer_payment_received(
        self,
        db: Session,
        booking: Any
    ) -> Dict[str, Any]:
        """
        Notify customer that their payment has been received and is under review.
        
        Args:
            db: Database session
            booking: Booking instance with related user
            
        Returns:
            Dict containing:
                - success (bool): Whether notification was sent
                - message (str): Status message
                - error (str): Error message if failed
        """
        try:
            message = f"""📸 *Payment Screenshot Received!*

⏱️ *Verification Status:*
🔍 Under Review (Usually takes 5-10 minutes)
✅ You'll get confirmation message once verified

Thank you for your patience! 😊"""
            
            # Determine routing based on user's session source
            user_session = self.session_repo.get_by_user_id(db, booking.user_id)
            
            if user_session and user_session.source == "Website":
                # Website booking - save to user's chat
                return await self._send_to_web_user(db, booking.user_id, message)
            elif user_session and user_session.source == "Chatbot":
                # Chatbot (WhatsApp) booking
                if booking.user.phone_number:
                    return await self._send_to_whatsapp_user(
                        db,
                        booking.user.phone_number,
                        booking.user_id,
                        message
                    )
                else:
                    # Fallback to web if no phone number
                    return await self._send_to_web_user(db, booking.user_id, message)
            else:
                # Unknown source - use fallback logic
                if booking.user.phone_number:
                    return await self._send_to_whatsapp_user(
                        db,
                        booking.user.phone_number,
                        booking.user_id,
                        message
                    )
                else:
                    return await self._send_to_web_user(db, booking.user_id, message)
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to notify customer: {str(e)}"
            }
    
    async def notify_booking_confirmed(
        self,
        db: Session,
        booking: Any,
        confirmed_by: str = "admin"
    ) -> Dict[str, Any]:
        """
        Notify customer that their booking has been confirmed.
        
        Args:
            db: Database session
            booking: Booking instance with related user and property
            confirmed_by: Who confirmed the booking (default: "admin")
            
        Returns:
            Dict containing:
                - success (bool): Whether notification was sent
                - message (str): Confirmation message sent
                - customer_phone (str): Customer phone number (if available)
                - error (str): Error message if failed
        """
        try:
            # Format booking date
            formatted_date = booking.booking_date.strftime("%d %B %Y (%A)")
            
            # Calculate advance and remaining amounts
            advance_percentage = booking.property.advance_percentage
            advance_amount = (advance_percentage / 100) * booking.total_cost
            remaining_amount = booking.total_cost - advance_amount
            
            message = f"""🎉 *BOOKING CONFIRMED!* ✅

Congratulations! Your payment has been verified and your booking is now confirmed!

📋 *Booking Details:*
🆔 Booking ID: `{booking.booking_id}`
🏠 Property: *{booking.property.name}*
📍 Location: {booking.property.address}
📅 Date: {formatted_date}
🕐 Shift: {booking.shift_type}
👥 Max Guests: {booking.property.max_occupancy}
💰 Total Amount: *Rs. {int(booking.total_cost)}*

💳 *Payment Status:*
✅ Advance Paid: Rs. {int(advance_amount)} ({advance_percentage}%)
⏳ Remaining: Rs. {int(remaining_amount)} (Pay on arrival)

━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *Important Information:*
• Please arrive on time for your booking
• Bring a valid ID for verification
• Pay remaining amount on arrival
• Contact us for any questions

📞 *Need Help?*
Feel free to reach out if you have any questions!

_We look forward to hosting you!_ 🎊"""
            
            # Determine routing based on user's session source
            user_session = self.session_repo.get_by_user_id(db, booking.user_id)
            
            if user_session and user_session.source == "Website":
                # Website booking
                result = await self._send_to_web_user(db, booking.user_id, message)
                result["customer_phone"] = None
                result["message"] = message
                return result
            elif user_session and user_session.source == "Chatbot":
                # Chatbot (WhatsApp) booking
                if booking.user.phone_number:
                    result = await self._send_to_whatsapp_user(
                        db,
                        booking.user.phone_number,
                        booking.user_id,
                        message
                    )
                    result["customer_phone"] = booking.user.phone_number
                    result["message"] = message
                    return result
                else:
                    result = await self._send_to_web_user(db, booking.user_id, message)
                    result["customer_phone"] = None
                    result["message"] = message
                    return result
            else:
                # Unknown source - use fallback
                if booking.user.phone_number:
                    result = await self._send_to_whatsapp_user(
                        db,
                        booking.user.phone_number,
                        booking.user_id,
                        message
                    )
                    result["customer_phone"] = booking.user.phone_number
                    result["message"] = message
                    return result
                else:
                    result = await self._send_to_web_user(db, booking.user_id, message)
                    result["customer_phone"] = None
                    result["message"] = message
                    return result
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send confirmation: {str(e)}"
            }
    
    async def notify_booking_cancelled(
        self,
        db: Session,
        booking: Any,
        reason: Optional[str] = None,
        cancelled_by: str = "user"
    ) -> Dict[str, Any]:
        """
        Notify customer that their booking has been cancelled.
        
        Args:
            db: Database session
            booking: Booking instance with related user
            reason: Optional cancellation reason
            cancelled_by: Who cancelled the booking (default: "user")
            
        Returns:
            Dict containing:
                - success (bool): Whether notification was sent
                - message (str): Cancellation message sent
                - error (str): Error message if failed
        """
        try:
            # Build cancellation message
            message = f"""❌ *BOOKING CANCELLED*

🆔 Booking ID: `{booking.booking_id}` has been cancelled.
"""
            
            # Add reason if provided
            if reason:
                message += f"\n📝 *Reason:* {reason}\n"
            
            # Add refund information if payment was made
            if booking.status in ["Waiting", "Confirmed"]:
                message += """
💰 *Refund Information:*
If you made any payment, please contact our support team for refund assistance.

📞 *Contact Support:*
We're here to help with any questions about your refund.
"""
            else:
                message += """
_No payment was processed for this booking._
"""
            
            message += """
_Feel free to make a new booking anytime!_ 😊"""
            
            # Determine routing based on user's session source
            user_session = self.session_repo.get_by_user_id(db, booking.user_id)
            
            if user_session and user_session.source == "Website":
                # Website booking
                return await self._send_to_web_user(db, booking.user_id, message)
            elif user_session and user_session.source == "Chatbot":
                # Chatbot (WhatsApp) booking
                if booking.user.phone_number:
                    return await self._send_to_whatsapp_user(
                        db,
                        booking.user.phone_number,
                        booking.user_id,
                        message
                    )
                else:
                    return await self._send_to_web_user(db, booking.user_id, message)
            else:
                # Unknown source - use fallback
                if booking.user.phone_number:
                    return await self._send_to_whatsapp_user(
                        db,
                        booking.user.phone_number,
                        booking.user_id,
                        message
                    )
                else:
                    return await self._send_to_web_user(db, booking.user_id, message)
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send cancellation notification: {str(e)}"
            }
    
    async def send_whatsapp_message(
        self,
        phone_number: str,
        message: str,
        user_id,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp message to a phone number.
        
        This is a public method for sending WhatsApp messages directly,
        useful for admin-initiated messages or custom notifications.
        
        Args:
            phone_number: Recipient's phone number
            message: Message content to send
            user_id: User ID for database tracking
            save_to_db: Whether to save the message to database (default: True)
            
        Returns:
            Dict containing:
                - success (bool): Whether message was sent
                - message_id (str): WhatsApp message ID if successful
                - error (str): Error message if failed
        """
        try:
            result = await self.whatsapp_client.send_message(
                recipient=phone_number,
                message=message
            )
            
            if result["success"]:
                # Save to database if requested
                if save_to_db:
                    self.message_repo.save_message(
                        db=None,  # Will need to be passed if save_to_db is True
                        user_id=user_id,
                        sender="bot",
                        content=message,
                        whatsapp_message_id=result.get("message_id")
                    )
                
                return {
                    "success": True,
                    "message_id": result.get("message_id"),
                    "message": "WhatsApp message sent successfully"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Failed to send WhatsApp message")
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send WhatsApp message: {str(e)}"
            }
    
    # Private helper methods for routing
    
    async def _send_to_web_admin(
        self,
        db: Session,
        message: str
    ) -> Dict[str, Any]:
        """Send message to web admin by saving to their chat."""
        try:
            # Save message to admin's conversation
            self.message_repo.save_message(
                db,
                user_id=WEB_ADMIN_USER_ID,
                sender="bot",
                content=message,
                whatsapp_message_id=None
            )
            
            return {
                "success": True,
                "message": "Notification sent to web admin",
                "channel": "web"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send to web admin: {str(e)}"
            }
    
    async def _send_to_whatsapp_admin(
        self,
        db: Session,
        message: str
    ) -> Dict[str, Any]:
        """Send message to WhatsApp admin."""
        try:
            result = await self.whatsapp_client.send_message(
                recipient=VERIFICATION_WHATSAPP,
                message=message
            )
            
            if result["success"]:
                # Save to database
                self.message_repo.save_message(
                    db,
                    user_id=None,  # Admin messages might not have user_id
                    sender="bot",
                    content=message,
                    whatsapp_message_id=result.get("message_id")
                )
                
                return {
                    "success": True,
                    "message": "Notification sent to WhatsApp admin",
                    "channel": "whatsapp"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Failed to send WhatsApp message")
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send to WhatsApp admin: {str(e)}"
            }
    
    async def _send_to_web_user(
        self,
        db: Session,
        user_id,
        message: str
    ) -> Dict[str, Any]:
        """Send message to web user by saving to their chat."""
        try:
            self.message_repo.save_message(
                db,
                user_id=user_id,
                sender="bot",
                content=message,
                whatsapp_message_id=None
            )
            
            return {
                "success": True,
                "message": "Notification sent to web user",
                "channel": "web"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send to web user: {str(e)}"
            }
    
    async def _send_to_whatsapp_user(
        self,
        db: Session,
        phone_number: str,
        user_id,
        message: str
    ) -> Dict[str, Any]:
        """Send message to WhatsApp user."""
        try:
            result = await self.whatsapp_client.send_message(
                recipient=phone_number,
                message=message
            )
            
            if result["success"]:
                # Save to database
                self.message_repo.save_message(
                    db,
                    user_id=user_id,
                    sender="bot",
                    content=message,
                    whatsapp_message_id=result.get("message_id")
                )
                
                return {
                    "success": True,
                    "message": "Notification sent to WhatsApp user",
                    "channel": "whatsapp"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Failed to send WhatsApp message")
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send to WhatsApp user: {str(e)}"
            }
