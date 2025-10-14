# booking_tools.py - Complete Fixed Version with Web and WhatsApp Admin Support

from langchain.tools import tool
from langchain_core.tools import StructuredTool
from app.database import SessionLocal
from app.chatbot.models import (
    Property, PropertyImage, PropertyAmenity, PropertyPricing, PropertyVideo,
    OwnerProperty, Owner, User, Booking, Session, Message
)
from sqlalchemy import text, and_,desc,asc
from typing import List, Dict, Optional
import uuid
from datetime import datetime, timedelta
import os
import re
import base64
import requests
import json
from PIL import Image
import io
import asyncio
import httpx
import google.generativeai as genai
import threading
from concurrent.futures import ThreadPoolExecutor
import time

# Configuration
EASYPAISA_NUMBER = "03155699929"
VERIFICATION_WHATSAPP = "923155699929"
WEB_ADMIN_USER_ID = uuid.UUID("216d5ab6-e8ef-4a5c-8b7c-45be19b28334")  # UUID object, not string
WHATSAPP_TOKEN = os.getenv("META_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def get_or_create_user(wa_id: str, db) -> uuid.UUID:
    user = db.query(User).filter_by(phone_number=wa_id).first()
    if user:
        return user.user_id
    user_id = uuid.uuid4()  # UUID object, not string
    new_user = User(user_id=user_id, phone_number=wa_id, created_at=datetime.utcnow())
    db.add(new_user)
    db.commit()
    return user_id

def get_or_create_admin_session(user_id: uuid.UUID, db) -> str:
    """Get or create session for admin user, refreshing if expired"""
    session = db.query(Session).filter_by(user_id=user_id).first()
    
    # Check if session exists and is not expired (1 hour inactivity)
    if session:
        time_since_update = datetime.utcnow() - session.updated_at
        if time_since_update < timedelta(hours=1):
            # Update timestamp to keep session alive
            session.updated_at = datetime.utcnow()
            db.commit()
            return session.id
        else:
            # Session expired, delete and create new one
            db.delete(session)
            db.commit()
    
    # Create new session
    session_id = str(uuid.uuid4())
    new_session = Session(
        id=session_id, 
        user_id=user_id,  # UUID object
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_session)
    db.commit()
    return session_id

def send_whatsapp_message_sync(recipient_number: str, message: str, user_id: uuid.UUID = None, save_to_db: bool = True) -> dict:
    """
    Synchronous WhatsApp message sender with database integration
    
    Args:
        recipient_number: Phone number to send message to
        message: Message content
        user_id: User ID for database record (UUID object, required if save_to_db=True)
        save_to_db: Whether to save message to database
        
    Returns:
        dict: {"success": bool, "whatsapp_message_id": str, "message_db_id": int}
    """
    try:
        url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_number,
            "type": "text",
            "text": {"body": message}
        }
        
        # Send message to WhatsApp
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Extract WhatsApp message ID from response
            response_data = response.json()
            whatsapp_msg_id = response_data.get("messages", [{}])[0].get("id", "")
            
            # Save to database if requested
            message_db_id = None
            if save_to_db and user_id:
                message_db_id = save_bot_message_to_db(
                    user_id=user_id,
                    content=message,
                    whatsapp_message_id=whatsapp_msg_id
                )
            
            return {
                "success": True,
                "whatsapp_message_id": whatsapp_msg_id,
                "message_db_id": message_db_id
            }
        else:
            print(f"❌ WhatsApp API Error: {response.status_code} - {response.text}")
            return {"success": False, "whatsapp_message_id": None, "message_db_id": None}
            
    except Exception as e:
        print(f"❌ Error sending WhatsApp message: {e}")
        return {"success": False, "whatsapp_message_id": None, "message_db_id": None}

def save_web_message_to_db(user_id: uuid.UUID, content: str, sender: str = "bot") -> int:
    """
    Save web message to database (no WhatsApp ID)
    
    Args:
        user_id: User ID (UUID object)
        content: Message content
        sender: "bot" or "user"
        
    Returns:
        int: Database message ID
    """
    db = SessionLocal()
    try:
        message = Message(
            user_id=user_id,
            sender=sender,
            content=content,
            whatsapp_message_id=None,  # No WhatsApp ID for web messages
            timestamp=datetime.utcnow()
        )
        
        db.add(message)
        db.commit()
        
        print(f"✅ Web message saved to DB - ID: {message.id}, Sender: {sender}, User: {user_id}")
        return message.id
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error saving web message to database: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return None
    finally:
        db.close()

def save_bot_message_to_db(user_id: uuid.UUID, content: str, whatsapp_message_id: str) -> int:
    """
    Save bot message to database
    
    Args:
        user_id: User ID from session (UUID object)
        content: Message content
        whatsapp_message_id: WhatsApp's message ID
        
    Returns:
        int: Database message ID
    """
    from app.agent.booking_agent import BookingToolAgent  # Import here to avoid circular import
    
    db = SessionLocal()
    try:
        # Create message record
        message = Message(
            user_id=user_id,
            sender="bot",
            content=content,
            whatsapp_message_id=whatsapp_message_id,
            timestamp=datetime.utcnow()
        )
        
        db.add(message)
        db.commit()
        
        print(f"✅ Bot message saved to DB - ID: {message.id}, WhatsApp ID: {whatsapp_message_id}, User: {user_id}")
        return message.id
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error saving bot message to database: {e}")
        return None
    finally:
        db.close()

def send_verification_request_sync(booking_details: Dict, payment_details: Dict, is_web: bool = False) -> bool:
    """
    Send verification request to admin (WhatsApp or Web)
    
    Args:
        booking_details: Booking information
        payment_details: Payment information
        is_web: If True, send to web admin; if False, send to WhatsApp
    """
    try:
        # Build payment details section with optional fields
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
        
        message = f"""🔔 *PAYMENT VERIFICATION REQUEST*

📋 *Booking Details:*
🆔 Booking ID: `{booking_details['booking_id']}`
🏠 Property: {booking_details['property_name']}
📅 Date: {booking_details['booking_date']}
🕐 Shift: {booking_details['shift_type']}
💰 Expected Amount: Rs. {booking_details['amount']}
👤 Customer Name: {booking_details['customer_name']}
📱 Customer Phone: {booking_details['customer_phone']}

💳 *Payment Details Provided:*
{chr(10).join(payment_info)}

✅ To CONFIRM: Reply `confirm {booking_details['booking_id']}`
❌ To REJECT: Reply `reject {booking_details['booking_id']} [reason]`

*Common Rejection Reasons:*
• amount_mismatch - Wrong amount paid
• transaction_not_found - Can't verify transaction
• insufficient_amount - Amount less than required
• incorrect_receiver - Wrong EasyPaisa number
• duplicate_transaction - Transaction already used
• invalid_details - Details don't match

Examples:
• `confirm {booking_details['booking_id']}`
• `reject {booking_details['booking_id']} amount_mismatch`
• `reject {booking_details['booking_id']} insufficient_amount`"""
        
        db = SessionLocal()
        try:
            if is_web:
                # Send to web admin
                admin_user_id = WEB_ADMIN_USER_ID
                
                # Ensure admin user exists
                admin_user = db.query(User).filter_by(user_id=admin_user_id).first()
                if not admin_user:
                    print(f"❌ Web admin user {admin_user_id} not found")
                    return False
                
                # Get or create admin session (handles expiration)
                admin_session_id = get_or_create_admin_session(admin_user_id, db)
                
                # Save message to admin's conversation
                save_web_message_to_db(admin_user_id, message, sender="bot")
                
                print(f"✅ Verification request sent to web admin (session: {admin_session_id})")
                return True
            else:
                # Send to WhatsApp admin
                user = db.query(User).filter_by(phone_number=VERIFICATION_WHATSAPP).first()
                if user:
                    user_id = user.user_id
                else:
                    user_id = get_or_create_user(VERIFICATION_WHATSAPP, db)
                
                result = send_whatsapp_message_sync(VERIFICATION_WHATSAPP, message, user_id, save_to_db=True)
                return result["success"]
        finally:
            db.close()
        
    except Exception as e:
        print(f"❌ Error sending verification request: {e}")
        return False

def run_async_verification(booking_details: Dict, payment_details: Dict, is_web: bool = False) -> bool:
    """Run verification with improved error handling and fallback methods"""
    
    # Check if required environment variables are set for WhatsApp
    if not is_web and (not WHATSAPP_TOKEN or not PHONE_NUMBER_ID or not VERIFICATION_WHATSAPP):
        print("❌ Missing WhatsApp configuration (TOKEN, PHONE_NUMBER_ID, or VERIFICATION_WHATSAPP)")
        return False
    
    # Try sending the verification message
    try:
        print(f"🔄 Attempting to send verification message ({'Web' if is_web else 'WhatsApp'})...")
        success = send_verification_request_sync(booking_details, payment_details, is_web)
        
        if success:
            print(f"✅ Verification message sent successfully ({'Web' if is_web else 'WhatsApp'})")
            return True
        else:
            print("❌ Failed to send verification message")
            return False
            
    except Exception as e:
        print(f"❌ Critical error in run_async_verification: {e}")
        return False

def remove_dash_from_cnic(cnic:str):
    return cnic.replace("-", "")

@tool("create_booking",return_direct=True)
def create_booking(
    session_id: str,
    booking_date: str,
    shift_type: str,
    cnic: Optional[str] = None,
    user_name: Optional[str] = None
) -> dict:
    """
    Create a new property booking when user wants to book, reserve, or rent a property/farm/venue.
    Use this when user says they want to book, reserve, rent, or says phrases like:
    - "I want to book a farm/property"
    - "Book karna hai", "farm book krna hai"
    - "Reserve this property"
    - "I want this venue"
    - "Book kar do"
    
    Args:
        session_id: Current chat session ID
        user_name: Customer's full name
        booking_date: Date in YYYY-MM-DD format
        shift_type: "Day", "Night", "Full Day", or "Full Night"
        cnic: Customer's CNIC number
    
    Returns booking confirmation with payment instructions.
    """
    
    db = SessionLocal()
    try:
        # Get session details for user phone
        session = db.query(Session).filter_by(id=session_id).first()
        
        if not session or not session.property_id:
            return {"error": "Please provide me name of the property."}
        
        property_id = session.property_id
        
        if (cnic is None and not session.user.cnic) and (user_name is None and not session.user.name):
            return {"error": "Please provide me your Full name and CNIC for booking"}
        
        elif cnic is None and not session.user.cnic:
            return {"error":"Please provide your CNIC for booking"}

        elif user_name is None and not session.user.name:
            return {"error": "Please provide me your Full name for booking"}

        if cnic and not session.user.cnic:
            cnic = remove_dash_from_cnic(cnic)
            if len(cnic)!=13:
                return {"error":"Please enter 13 digit CNIC"}
            
            session.user.cnic = cnic

        if user_name and not session.user.name:
            session.user.name = user_name
            db.commit()
            
        user_phone = session.user.phone_number
        user_id = session.user.user_id
        
        # Calculate day of week from booking date
        try:
            date_obj = datetime.strptime(booking_date, "%Y-%m-%d")
            day_of_week = date_obj.strftime("%A").lower()
        except ValueError:
            return {"error": "❌ Invalid date format. Please use YYYY-MM-DD format."}
        
        # Get property pricing and details
        pricing_sql = """
            SELECT psp.price, p.name, p.max_occupancy, p.address
            FROM property_pricing pp
            JOIN property_shift_pricing psp ON pp.pricing_id = psp.pricing_id
            JOIN properties p ON pp.property_id = p.property_id
            WHERE pp.property_id = :property_id
            AND psp.day_of_week = :day_of_week
            AND psp.shift_type = :shift_type
        """
        
        result = db.execute(text(pricing_sql), {
            "property_id": property_id,
            "day_of_week": day_of_week,
            "shift_type": shift_type
        }).first()
        
        if not result:
            return {"error": f"❌ Pricing not found for {shift_type} shift on {day_of_week}. Please contact support."}
        
        total_cost, property_name, max_occupancy, address = result
        
        # Validate shift type
        valid_shifts = ["Day", "Night", "Full Day", "Full Night"]
        if shift_type not in valid_shifts:
            return {"error": "❌ Invalid shift type. Please choose 'Day', 'Night', 'Full Day', or 'Full Night'"}
        
        # Check if already booked
        existing_booking_sql = """
            SELECT 1 FROM bookings
            WHERE property_id = :property_id 
            AND booking_date = :booking_date
            AND shift_type = :shift_type
            AND status IN ('Pending', 'Confirmed')
        """
        existing = db.execute(text(existing_booking_sql), {
            "property_id": property_id,
            "booking_date": booking_date,
            "shift_type": shift_type
        }).first()
        
        if existing:
            return {"error": f"❌ Sorry! {property_name} is already booked for {booking_date} ({shift_type} shift). Please choose a different date or shift."}
        
        # Create booking with pending status
        booking_id = session.user.name + "-" + booking_date + "-" + shift_type
        session.booking_id = booking_id
        db.commit()
        
        booking = Booking(
            booking_id=booking_id,
            user_id=user_id,
            property_id=property_id,
            booking_date=datetime.strptime(booking_date, "%Y-%m-%d").date(),
            shift_type=shift_type,
            total_cost=total_cost,
            booking_source="Bot",
            status="Pending",
            booked_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(booking)
        db.commit()
        
        # Format date for display
        try:
            date_obj = datetime.strptime(booking_date, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d %B %Y (%A)")
        except:
            formatted_date = booking_date
        
        adv = booking.property.advance_percentage
        cost_to_pay = (adv/100)*total_cost
        remaining_amount = total_cost - cost_to_pay
        
        message = f"""🎉 *Booking Request Created Successfully!*

📋 *Booking Details:*
🆔 Booking ID: `{booking_id}`
🏠 Property: *{property_name}*
📍 Location: {address}
📅 Date: {formatted_date}
🕐 Shift: {shift_type}
👥 Max Guests: {max_occupancy}
💰 Total Amount: *Rs. {int(total_cost)}*

━━━━━━━━━━━━━━━━━━━━━━━━━

💳 *PAYMENT INSTRUCTIONS:*

Please send {booking.property.advance_percentage}% advance *Rs. {int(cost_to_pay)}* to:
📱 EasyPaisa Number: *{EASYPAISA_NUMBER}*
✍🏼 Account Holder Name : *SYED MUHAMMAD BILAL*

Pay remaining Amount *Rs: {int(remaining_amount)}* on the {booking.property.type}

📸 *After Making Payment:*
1️⃣ Send me the payment screenshot, OR
2️⃣ Provide these payment details:
   • Your full name (as sender) ✅ Required
   • Amount paid ✅ Required
   • Transaction ID (if available) ⚪ Optional
   • Your phone number (if different) ⚪ Optional

━━━━━━━━━━━━━━━━━━━━━━━━━

✅ *Verification Process:*
• Our team will verify your payment
• You'll get confirmation within 5-10 minutes
• Then your booking will be confirmed!

⚠️ *Important Notes:*
• Complete payment within 30 minutes
• Keep your payment proof safe
• Payment must match exact amount: Rs. {int(total_cost)}

_Ready to pay? Send your payment proof after completing the transaction!_ 😊"""
        
        return {
            "message": message,
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating booking: {e}")
        return {"error": f"❌ Something went wrong while creating your booking. Please try again or contact support."}
    finally:
        db.close()

@tool("process_payment_screenshot" , return_direct=True)
def process_payment_screenshot(booking_id: str = None) -> dict:
    """Process payment screenshot for a booking.
    If no booking ID is provided, return False.
    Else, return Payment details.
    """
    if not booking_id:
        return False

    db = SessionLocal()
    booking = db.query(Booking).filter_by(booking_id=booking_id).first()

    booking_date =  booking.booking_date.strftime("%d-%m-%Y")
    shift_type = booking.shift_type 
    property_name = booking.property.name 
    property_type = booking.property.type
    total_cost = booking.total_cost
    user_phone = booking.user.phone_number
    user_cnic = booking.user.cnic    
    booking.status = "Waiting"
    message = f"""📸 *Payment Screenshot Received!*

Booking ID: `{booking_id}`
Property: *{property_name}*
Type: {property_type}
Date: {booking_date}
Shift: {shift_type}
Total Amount: *Rs. {int(total_cost)}*
User Phone: {user_phone}
User CNIC: {user_cnic}

Please verify the payment by looking at the screenshot.

To confirm : confirm `{booking_id}`
To reject : reject `{booking_id}` [reason]
    """

    client_message = f"""📸 *Payment Screenshot Received!*

⏱️ *Verification Status:*
🔍 Under Review (Usually takes 5-10 minutes)
✅ You'll get confirmation message once verified

Thank you for your patience! 😊
"""
    
    # Determine if this is a web or WhatsApp booking
    is_web_booking = user_phone is None or user_phone == ""
    
    if is_web_booking:
        # For web bookings, save confirmation to user's chat
        save_web_message_to_db(booking.user_id, client_message, sender="bot")
    else:
        # For WhatsApp bookings, send via WhatsApp
        send_whatsapp_message_sync(user_phone, client_message, booking.user.user_id, save_to_db=True)
    
    return message

@tool("process_payment_details")
def process_payment_details(
    session_id: str,
    booking_id: str,
    transaction_id: Optional[str] = None,
    sender_name: Optional[str] = None,
    amount: Optional[str] = None,
    sender_phone: Optional[str] = None
) -> dict:
    """
    Process manual payment details when user provides transaction info via text.
    Use when user gives payment information like:
    - "Transaction ID: TXN123456"
    - "I paid 5000 rupees"
    - "My transaction ID is ABC123"
    - Provides payment details in text format
    
    Args:
        session_id: Current session ID
        booking_id: Booking ID for payment
        transaction_id: Payment transaction/reference ID (optional)
        sender_name: Name of person who made payment
        amount: Amount paid
        sender_phone: Phone number of sender (optional)
        
    Returns verification status and next steps.
    """
    db = SessionLocal()
    try:
        booking_id = booking_id.strip()
        booking = db.query(Booking).filter_by(booking_id=booking_id).first()
        
        if not booking:
            return {"error": "❌ Booking not found. Please check your booking ID."}
        
        # Combine provided details
        payment_details = {
            'transaction_id': transaction_id,
            'sender_name': sender_name,
            'amount': amount,
            'sender_phone': sender_phone,
            'receiver_phone': EASYPAISA_NUMBER,
        }
        
        # Clean and validate details
        if payment_details['transaction_id']:
            payment_details['transaction_id'] = re.sub(r'[^A-Z0-9]', '', payment_details['transaction_id'].upper())
        
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
        
        # Get property details
        property_sql = "SELECT name FROM properties WHERE property_id = :property_id"
        property_result = db.execute(text(property_sql), {"property_id": booking.property_id}).first()
        property_name = property_result[0] if property_result else "Unknown Property"
        
        # Determine if this is a web or WhatsApp booking
        session = db.query(Session).filter_by(id=session_id).first()
        is_web_booking = session.user.phone_number is None or session.user.phone_number == ""
        
        # Prepare booking details for admin verification
        booking_details = {
            'client_session_id': session_id,
            'booking_id': str(booking.booking_id),
            'property_name': property_name,
            'booking_date': booking.booking_date.strftime("%d %B %Y"),
            'shift_type': booking.shift_type,
            'amount': int(booking.total_cost),
            'customer_name': payment_details['sender_name'],
            'customer_phone': booking.user.phone_number or "Web User",
        }
        
        # Send verification request (web or WhatsApp based on booking source)
        try:
            verification_sent = run_async_verification(booking_details, payment_details, is_web=is_web_booking)
        except Exception as e:
            print(f"❌ Error sending verification: {e}")
            verification_sent = False
        
        if verification_sent:
            # Store payment details temporarily
            booking.updated_at = datetime.now()
            db.commit()
            
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
            
            return {
                "success": True,
                "message": f"""✅ *Payment Details Received*

Your payment is being verified by our team.

📋 *Details Submitted:*
{chr(10).join(submitted_details)}

⏱️ *Verification Status:*
🔍 Under Review (Usually takes 5-10 minutes)
✅ You'll get confirmation message once verified

Thank you for your patience! 😊

_Keep this conversation open to receive your confirmation._""",
                "status": "verification_pending"
            }
        else:
            return {
                "success": False,
                "message": "❌ Error sending payment for verification. Please try again in a moment or contact our support team."
            }
        
    except Exception as e:
        print(f"❌ Error processing payment details: {e}")
        return {"error": "❌ Error processing payment details. Please try again or contact support."}
    finally:
        db.close()

@tool("confirm_booking_payment")
def confirm_booking_payment(booking_id: str) -> dict:
    """
    Confirm booking after admin verification (internal use).
    Admin Agent can call this tool to confirm a booking after verifying payment.
    Returns customer_phone and message for webhook to send to customer.
    """
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter_by(booking_id=booking_id).first()
        
        if not booking:
            return {"error": "❌ Booking not found"}
        
        if booking.status == "Confirmed":
            return {
                "success": True,
                "already_confirmed": True,
                "message": "✅ Booking already confirmed",
                "customer_phone": booking.user.phone_number,
                "customer_user_id": booking.user.user_id
            }
        
        # Update booking status to confirmed
        booking.status = "Confirmed"
        booking.updated_at = datetime.now()
        db.commit()
        
        # Get property details for confirmation message
        property_sql = "SELECT name, address, contact_number FROM properties WHERE property_id = :property_id"
        property_result = db.execute(text(property_sql), {"property_id": booking.property_id}).first()
        
        if property_result:
            property_name, property_address, property_contact = property_result
        else:
            property_name = "Your Selected Property"
            property_address = "Address will be shared separately"
            property_contact = "Contact details will be provided"
        
        # Format confirmation message for customer
        formatted_date = booking.booking_date.strftime("%d %B %Y (%A)")
        
        confirmation_message = f"""🎉 *BOOKING CONFIRMED!* ✅

Congratulations! Your payment has been verified and your booking is now confirmed!

📋 *Booking Details:*
🆔 Booking ID: `{booking_id}`
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

        # Return data for webhook to send to customer
        return {
            "success": True,
            "customer_phone": booking.user.phone_number,
            "customer_user_id": booking.user.user_id,
            "message": confirmation_message
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error confirming booking: {e}")
        return {"error": f"❌ Error confirming booking: {str(e)}"}
    finally:
        db.close()

@tool("reject_booking_payment")
def reject_booking_payment(booking_id: str, reason: str = None) -> dict:
    """
    Reject booking payment after admin review (internal use).
    This is called automatically when admin rejects payment.
    Make sure the reason is formatted and explained clearly.
    Returns customer_phone and message for webhook to send to customer.
    """
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter_by(booking_id=booking_id).first()
        
        if not booking:
            return {"error": "❌ Booking not found"}
        
        # Get property name
        property_sql = "SELECT name FROM properties WHERE property_id = :property_id"
        property_result = db.execute(text(property_sql), {"property_id": booking.property_id}).first()
        property_name = property_result[0] if property_result else "Your Property"
        
        rejection_message = f"""❌ *PAYMENT VERIFICATION FAILED*

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
   • Account Name: HutBuddy

2️⃣ *Send Payment Proof:*
   • Clear screenshot of payment confirmation
   • Or provide: Your Name ✅, Amount ✅, Transaction ID ⚪ (optional)

━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ *Your booking is still RESERVED for 30 minutes*

Need help? Contact our support team or try the payment again.

_We're here to help you complete your booking!_ 😊"""
        
        # Return data for webhook to send to customer
        return {
            "success": True,
            "customer_phone": booking.user.phone_number,
            "customer_user_id": booking.user.user_id,
            "message": rejection_message,
            "booking_status": "Pending",
            "reason": reason
        }
        
    except Exception as e:
        print(f"❌ Error rejecting payment: {e}")
        return {"error": f"❌ Error rejecting payment: {str(e)}"}
    finally:
        db.close()

@tool("check_booking_status")
def check_booking_status(booking_id: str) -> dict:
    """
    Check current status of any booking when user asks about their booking.
    Use when user wants to:
    - Check booking status
    - "Mera booking ka status kya hai"
    - "Is my booking confirmed?"
    - "What's the status of my reservation?"
    - Asks about their booking progress
    
    Args:
        booking_id: The booking ID to check
        
    Returns current booking status and details.
    """
    db = SessionLocal()
    try:
        booking_id = booking_id.strip()
        booking = db.query(Booking).filter_by(booking_id=booking_id).first()
        
        if not booking:
            return {"error": "❌ Booking not found. Please check your booking ID."}
        
        # Get property name
        property_sql = "SELECT name FROM properties WHERE property_id = :property_id"
        property_result = db.execute(text(property_sql), {"property_id": booking.property_id}).first()
        property_name = property_result[0] if property_result else "Unknown Property"
        
        # Format date
        try:
            formatted_date = booking.booking_date.strftime("%d %B %Y (%A)")
        except:
            formatted_date = str(booking.booking_date)
        
        # Status-specific messages
        status_messages = {
            "Pending": f"""⏳ *Awaiting Payment*

💳 *Payment Required:*
Amount: Rs. {int(booking.total_cost)}
EasyPaisa: {EASYPAISA_NUMBER}

📸 After payment, send screenshot or payment details:
• Your name ✅ Required
• Amount paid ✅ Required  
• Transaction ID ⚪ Optional""",
            
            "Confirmed": """✅ *Booking Confirmed!*
Your booking is confirmed. Enjoy your visit!""",
            
            "Cancelled": "❌ *Booking Cancelled*",
            "Completed": "🎉 *Booking Completed Successfully!*"
        }
        
        message = f"""📋 *BOOKING STATUS*

🆔 Booking ID: `{booking.booking_id}`
🏠 Property: *{property_name}*
📅 Date: {formatted_date}
🕐 Shift: {booking.shift_type}
💰 Amount: Rs. {int(booking.total_cost)}

━━━━━━━━━━━━━━━━━━━━━━━━━

📊 {status_messages.get(booking.status, f"Status: {booking.status}")}"""
        
        return {
            "success": True,
            "status": booking.status,
            "message": message,
            "booking_id": str(booking.booking_id),
            "needs_payment": booking.status == "Pending",
            "property_name": property_name,
            "amount": float(booking.total_cost)
        }
        
    except Exception as e:
        print(f"❌ Error checking booking status: {e}")
        return {"error": "❌ Error checking booking status. Please try again."}
    finally:
        db.close()

@tool("cancel_booking")
def cancel_booking(booking_id: str, session_id: str) -> dict:
    """
    Cancel a pending booking when user wants to cancel their reservation.
    Use when user says:
    - "Cancel my booking"
    - "I want to cancel"
    - "Cancel kar do"
    - "Remove my reservation"
    - Wants to cancel their booking
    
    Args:
        booking_id: ID of booking to cancel
        session_id: Current session ID for verification
        
    Returns cancellation confirmation.
    """
    db = SessionLocal()
    try:
        booking_id = booking_id.strip()
        booking = db.query(Booking).filter_by(booking_id=booking_id).first()
        
        if not booking:
            return {"error": "❌ Booking not found"}
        
        # Get session to verify user
        session = db.query(Session).filter_by(id=session_id).first()
        if not session or session.user_id != booking.user_id:
            return {"error": "❌ You can only cancel your own bookings"}
        
        if booking.status == "Confirmed":
            return {"error": "❌ Cannot cancel confirmed bookings. Please contact support for assistance and refund policies."}
        
        if booking.status == "Cancelled":
            return {"error": "❌ Booking is already cancelled"}
        
        # Cancel the booking
        booking.status = "Cancelled"
        booking.updated_at = datetime.now()
        db.commit()
        
        return {
            "success": True,
            "message": f"""✅ *Booking Cancelled Successfully*

🆔 Booking ID: `{booking_id}` has been cancelled.

If you made any payment, please contact our support team for refund assistance.

You can create a new booking anytime! 😊"""
        }
        
    except Exception as e:
        print(f"❌ Error cancelling booking: {e}")
        return {"error": "❌ Error cancelling booking. Please try again."}
    finally:
        db.close()

@tool("get_payment_instructions")
def get_payment_instructions(booking_id: str) -> dict:
    """
    Get payment instructions for pending bookings when user asks how to pay.
    Use when user asks:
    - "How do I pay?"
    - "Payment kaise karu?"
    - "What are payment details?"
    - "Where to send money?"
    - Needs payment guidance
    
    Args:
        booking_id: Booking ID needing payment
        
    Returns detailed payment instructions.
    """
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter_by(booking_id=booking_id).first()
        
        if not booking:
            return {"error": "❌ Booking not found"}
        
        if booking.status != "Pending":
            return {"error": f"❌ This booking is {booking.status.lower()}. No payment needed."}
        
        message = f"""💳 *PAYMENT INSTRUCTIONS*

🆔 Booking ID: `{booking.booking_id}`
💰 Amount to Pay: *Rs. {int(booking.total_cost)}*

━━━━━━━━━━━━━━━━━━━━━━━━━

📱 *EasyPaisa Payment:*
Send Rs. {int(booking.total_cost)} to: *{EASYPAISA_NUMBER}*

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
        
        return {
            "success": True,
            "message": message,
            "amount": float(booking.total_cost),
            "easypaisa_number": EASYPAISA_NUMBER
        }
        
    except Exception as e:
        print(f"❌ Error getting payment instructions: {e}")
        return {"error": "❌ Error retrieving payment instructions"}
    finally:
        db.close()

@tool("get_user_bookings")
def get_user_bookings(session_id: str, cnic: Optional[str] = None, limit: int = 5) -> dict:
    """
    Get user's recent bookings when they ask about their bookings.
    Use when user asks:
    - "Show my bookings"
    - "Mere bookings dikhao"
    - "What are my reservations?"
    - "My booking history"
    
    Args:
        session_id: Current session ID to identify user
        cnic: User's CNIC for verification
        limit: Maximum number of bookings to return
        
    Returns user's recent bookings list.
    """
    db = SessionLocal()
    try:
        # Get session to find user
        session = db.query(Session).filter_by(id=session_id).first()
        if not session:
            return {"error": "❌ Session not found. Please restart the conversation."}
        if not cnic:
            return {"error": "Please provide me CNIC number which you used to confirm booking."}
        
        user_phone = session.user.phone_number
        user_cnic = session.user.cnic
        user_id = session.user.user_id
        cnic = remove_dash_from_cnic(cnic)
        
        if user_cnic == cnic:
            results = (
                db.query(
                    Booking.booking_id,
                    Booking.status,
                    Booking.booking_date,
                    Booking.shift_type,
                    Booking.total_cost,
                    Booking.created_at,
                    Property.name.label('property_name')
                )
                .join(Property, Booking.property_id == Property.property_id)
                .filter(Booking.user_id == user_id)
                .order_by(desc(Booking.created_at))
                .limit(limit)
                .all()
            )
        else:
            return {"error": "❌ CNIC does not match our records. Please provide the correct CNIC."}
        
        if not results:
            return {
                "success": True,
                "message": """📋 *YOUR BOOKINGS*

No bookings found yet.

Ready to make your first booking? Just tell me what kind of property you're looking for! 🏡"""
            }
        
        bookings_list = []
        for result in results:
            booking_id, status, booking_date, shift_type, total_cost, created_at, property_name = result
            
            # Format date
            try:
                formatted_date = booking_date.strftime("%d %b %Y")
            except:
                formatted_date = str(booking_date)
            
            # Status emoji
            status_emoji = {
                "Pending": "⏳",
                "Confirmed": "✅", 
                "Cancelled": "❌",
                "Completed": "🎉"
            }.get(status, "📋")
            
            booking_info = f"""{status_emoji} *{property_name}*
📅 {formatted_date} | {shift_type}
💰 Rs. {int(total_cost)} | {status}
🆔 `{booking_id}`"""
            
            bookings_list.append(booking_info)
        
        message = f"""📋 *YOUR RECENT BOOKINGS*

{chr(10).join(bookings_list)}

━━━━━━━━━━━━━━━━━━━━━━━━━

💡 *Quick Actions:*
• Check status: Share booking ID
• Need help: Contact support
• New booking: Tell me your requirements!"""
        
        return {
            "success": True,
            "message": message,
            "bookings_count": len(results)
        }
        
    except Exception as e:
        print(f"❌ Error getting user bookings: {e}")
        return {"error": "❌ Error retrieving your bookings. Please try again."}
    finally:
        db.close()

# Export all booking tools
booking_tools = [
    create_booking,
    process_payment_screenshot,
    process_payment_details,
    confirm_booking_payment,
    reject_booking_payment,
    check_booking_status,
    cancel_booking,
    get_payment_instructions,
    get_user_bookings
]