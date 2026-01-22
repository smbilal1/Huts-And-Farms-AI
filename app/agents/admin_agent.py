from datetime import date
from xml.parsers.expat import model
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import create_react_agent
from app.database import SessionLocal
from app.models import Session, Message
from langchain_google_genai import ChatGoogleGenerativeAI
import google.genai as genai
from app.core.config import settings

import os
from sqlalchemy import text
from typing import List, Tuple, Optional, Dict
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage

# Import refactored payment tools from new structure
from app.agents.tools.payment_tools import (
    confirm_booking_payment,
    reject_booking_payment
)

system_prompt = """
You are *ADMIN BOT*, you will receive a verification message from *HutFarm-Booking AI*, you will wait until admin verifies payment details, then you will send a message to the user that their booking is confirmed or cancelled
with the reason of cancellation.

✅ To CONFIRM: Reply `confirm <booking_id>`
❌ To REJECT: Reply `reject <booking_id> [reason]`

When admin says "confirm <booking_id>", you MUST use the confirm_booking_payment tool.
When admin says "reject <booking_id> [reason]", you MUST use the reject_booking_payment tool.

The tools will return a response containing customer_phone and message - you must return this data so the webhook can send it to the customer.

Chat History:
{chat_history}
"""

class AdminAgent:
    def __init__(self):
        # ✅ Add the booking tools
        self.tools = [confirm_booking_payment, reject_booking_payment]

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0,
            google_api_key=settings.GOOGLE_API_KEY
        )

        self.prompt = ChatPromptTemplate(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
    
    def convert_messages_to_langchain_format(self, messages: List[Message]) -> List:
        """Convert database Message objects to LangChain message format"""
        langchain_messages = []
        
        for msg in messages:
            # Assuming your Message model has 'content' and 'sender_type' or similar fields
            # Adjust these field names based on your actual Message model structure
            
            if hasattr(msg, 'sender') and msg.sender == 'user':
                langchain_messages.append(HumanMessage(content=msg.content))
            elif hasattr(msg, 'sender') and msg.sender == 'admin':
                langchain_messages.append(HumanMessage(content=msg.content))
            else:
                # Default to AI message if it's from the bot
                langchain_messages.append(AIMessage(content=msg.content))
                
        return langchain_messages
        
    def get_response(self, incoming_text: str, session_id: str):
        db = SessionLocal()
        try:
            session = db.query(Session).filter_by(id=session_id).first()
            user_id = session.user.user_id
            # --- Get chat history and convert to LangChain format ---
            chat_history_objects = db.query(Message).filter_by(user_id=user_id).order_by(Message.timestamp.asc()).all()
            chat_history = self.convert_messages_to_langchain_format(chat_history_objects)
            
            print(f"Chat history converted: {len(chat_history)} messages")
            
            print(f"📥 Admin input: {incoming_text}")
            
            # Convert chat history to messages format
            messages = []
            for msg in chat_history:
                messages.append(msg)
            
            # Add current message
            messages.append(HumanMessage(content=incoming_text))
            
            # Run agent with context
            response = self.agent.invoke({
                "messages": messages,
            })
            
            print(f"🤖 Agent response: {response}")
            
            # Extract the final message content
            if response and "messages" in response:
                return response["messages"][-1].content
            
            return str(response)
            
        except Exception as e:
            print(f"❌ Error in AdminAgent: {e}")
            return {"error": f"Error processing admin request: {str(e)}"}
        finally:
            db.close()
