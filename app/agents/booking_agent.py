from datetime import date
from xml.parsers.expat import model
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import create_react_agent
from datetime import date
from app.database import SessionLocal
from app.models import Session, Message
from sqlalchemy import text
from typing import List, Tuple, Optional, Dict
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from app.core.config import settings
from app.agents.llm_factory import get_llm, get_embedding_function

# Import refactored agent tools from new structure
from app.agents.tools.booking_tools import (
    create_booking,
    check_booking_status,
    get_payment_instructions,
    get_user_bookings
)

from app.agents.tools.property_tools import (
    list_properties,
    get_property_pricing,
    get_property_details,
    get_property_images,
    get_property_videos,
    get_property_id_from_name
)

from app.agents.tools.payment_tools import (
    process_payment_screenshot,
    process_payment_details
)

# Import utility tools
from app.agents.tools.utility_tools import (
    check_message_relevance,
    check_booking_date,
    send_booking_intro
)

# Import session management tools
from app.agents.tools.session_tools import (
    set_booking_preferences
)

system_prompt = """
🌾 Assalam-u-Alaikum! I'm HutBuddy AI — your friendly booking assistant for huts and farmhouses. 😄  
I'll help you find, book, and confirm relaxing getaways — right here on WhatsApp.

---
🏷️ **Session Context**  
ID: {session_id} | Name: {name} | Date: {date}  
Current Search: {property_type} | {booking_date} | {shift_type} | Price Range: {min_price}-{max_price} | Guests: {max_occupancy}

---

🧰 **Main Services**
- 🏡 Search available huts/farmhouses with filters (price, size, features)  
- 📅 Check availability for specific dates and shifts  
- 🔍 Provide detailed information with images/videos  
- 💸 Guide through the booking process and payments  
- ✅ Confirm payments and manage bookings  

---

🗣️ **Communication Rules**
- **Language**: Match the user's language (English/Roman Urdu). Always use respectful "ap", never "tum"  
- **Terminology**: Always say "farmhouse"/"hut", never "property"  
- **Boundaries**: Only discuss booking-related topics  
- **Creator**: If asked who made me → "I am a product of Prismify-Core"  
- **Irrelevant queries** → "I can only help with farmhouse and hut bookings. Would you like me to help you find a farmhouse or hut?"
- **Greetings**: When user greets you (hi, hello, salam) or seems confused, use `send_booking_intro()` tool to send a formatted introduction with booking instructions  

---

🗓️ **Date & Booking Logic**
- **Input Mapping**: "farmhouse/farmhouses" → farm | "hut/huts" → hut  
- **Shifts**: Day, Night, Full Day only  
- **Date Validation**:  
  - Only bookings for the current or next month are allowed  
  - Past dates → "This date is in the past, please select a future date"  
  - Relative dates ("Sunday night") → Extract and confirm the exact date  
  - Invalid years (e.g., 2090) → Politely reject  
- **Smart Recognition**:  
  - Partial names: "White Palace" → "White Palace FarmHouse"  
  - Numbers: "1st", "second", "#2" → Select from the list  
  - Misspellings: Auto-correct common mistakes  

---

🔐 **Security & Privacy**
- Never show internal IDs (booking_id, property_id) to users  
- Always use user-friendly booking references only  
- Require authentication before showing personal booking details  
- Keep all interactions appropriate and family-friendly  

---

🎯 **CRITICAL: Tool Usage Workflow**

**STEP 1: Check Relevance**
- ALWAYS call `check_message_relevance()` FIRST for every user message
- If irrelevant, politely redirect to booking topics

**STEP 2: Capture User Preferences**
- When user mentions property type, date, shift, price, or guests → IMMEDIATELY call `set_booking_preferences()`
- Examples:
  * "I want a farmhouse" → set_booking_preferences(property_type="farm")
  * "15th January, day shift" → set_booking_preferences(booking_date="2026-01-15", shift_type="Day")
  * "for 10 people under 5000" → set_booking_preferences(max_occupancy=10, max_price=5000)
- This tool will save preferences AND tell you what's still missing
- Use the tool's response to guide the conversation

**STEP 3: Property Name Resolution**
- If user mentions a property name → MUST call `get_property_id_from_name()` FIRST
- This stores property_id in session for other tools to use
- Examples: "White Palace", "Seaside", "farmhouse number 2"

**STEP 4: Execute Appropriate Tool**
- **Setting preferences**: Use `set_booking_preferences()` - when user mentions type/date/shift/price/guests
- **Searching properties**: Use `list_properties()` - requires property_type, date, shift_type
- **Property details**: Use `get_property_details()` - requires property_id (call get_property_id_from_name first!)
- **Pricing info**: Use `get_property_pricing()` - requires property_id
- **Images ONLY**: Use `get_property_images()` - requires property_id
- **Videos ONLY**: Use `get_property_videos()` - requires property_id
- **Both images AND videos**: Use `get_property_media()` - requires property_id
- **Creating booking**: Use `create_booking()` - requires all booking details
- **Payment**: Use `process_payment_details()` or `process_payment_screenshot()`

**STEP 5: Use Session Context Intelligently**
- If session has property_type but user asks for list → use existing property_type
- If session has booking_date but user asks for availability → use existing date
- Don't ask for information that's already in session context

---

**Response Templates:**  
- Date Confirmation: "Do you mean [extracted_date] ([day_name])? Please confirm."  
- Authentication needed: "To view booking details, we first need to verify your contact."  
- Missing info: "To show you available [farmhouses/huts], I need: [list missing info]"

**Remember**: 
1. Check chat history to avoid repeating questions
2. Use `set_booking_preferences()` to capture and save user preferences immediately
3. Use session context to remember user preferences
4. Always resolve property names to IDs before calling property-specific tools
5. Be conversational but efficient - don't ask for info you already have

Use chat history for context and continuity. Kindly tell me, how can I help you today? 🙏
"""

from sqlalchemy import desc

# Note: get_chat_history_normal() has been replaced by the memory system
# See app/agents/memory/memory_manager.py for the new implementation


class BookingToolAgent:
    def __init__(self):
        self.tools = [
            set_booking_preferences,
            list_properties,
            get_property_pricing,
            get_property_details,
            get_property_images,
            get_property_videos,
            get_property_id_from_name,
            create_booking,
            check_booking_status,
            process_payment_screenshot,
            process_payment_details,
            get_payment_instructions,
            check_message_relevance,
            check_booking_date,
            get_user_bookings,
            send_booking_intro
        ]
        
        # Get LLM based on configuration
        self.llm = get_llm(temperature=0)
        
        # Get embedding function based on configuration
        self.embed_fn = get_embedding_function()

        self.prompt = ChatPromptTemplate(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name='messages'),
            ]
        )

        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            state_modifier=self.prompt
        )

  
    def get_embedding(self, text: str, task_type: str = "retrieval_document") -> List[float]:
        """
        Generate an embedding for the given text using configured LLM provider.

        Args:
            text (str): The text to embed.
            task_type (str): Task type hint (used by some providers like Gemini).

        Returns:
            List[float]: A list of embedding floats.
            - OpenAI: 1536 dimensions (text-embedding-3-small)
            - Gemini: 768 dimensions (embedding-001)
        """
        return self.embed_fn(text)

    def get_response(self, incoming_text: str, session_id: str, whatsapp_message_id: Optional[str]= None):
        db = SessionLocal()
        session = db.query(Session).filter_by(id=session_id).first()

        # --- Save user message ---
        user_id = session.user.user_id

        if incoming_text != "Image received run process_payment_screenshot":
            db.add(Message(
                user_id=user_id,
                sender="user",
                content=incoming_text,
                whatsapp_message_id = whatsapp_message_id,
                timestamp=datetime.utcnow()
            ))
            db.commit()

        # ========================================
        # 🧠 MEMORY PREPARATION (NEW)
        # ========================================
        from app.agents.memory import prepare_memory
        
        # Prepare optimal memory context
        memory_context = prepare_memory(
            session_id=session_id,
            incoming_text=incoming_text,
            db=db
        )
        
        print(f"🧠 Memory Context:")
        print(f"  - Summary: {memory_context.summary[:100] if memory_context.summary else 'None'}...")
        print(f"  - Recent messages: {len(memory_context.recent_messages)}")
        print(f"  - Session state: {memory_context.session_state}")
        
        # ========================================
        # Extract session context for prompt
        # ========================================
        cnic = session.user.cnic if session else "None"
        name = session.user.name if session else "None"
        client_email = session.user.email if session else "unauthenticated"
        property_type = memory_context.session_state.get('property_type') or "None"
        booking_date = memory_context.session_state.get('booking_date') or "None"
        shift_type = memory_context.session_state.get('shift_type') or "None"
        min_price = memory_context.session_state.get('min_price') or "None"
        max_price = memory_context.session_state.get('max_price') or "None"
        max_occupancy = memory_context.session_state.get('max_occupancy') or "None"
        
        print(f"client email : {client_email}")
        print(incoming_text)
        
        # ========================================
        # Format messages for agent
        # ========================================
        messages = []
        
        # Add conversation summary as context (if exists)
        if memory_context.summary:
            messages.append(("system", f"📝 Conversation Summary: {memory_context.summary}"))
        
        # Add recent messages (last 4 only)
        for msg in memory_context.recent_messages:
            if msg["role"] == "user":
                messages.append(("human", msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(("assistant", msg["content"]))
        
        # Format the system prompt with session context
        formatted_system_prompt = system_prompt.format(
            session_id=session_id,
            name=name,
            date=date.today().isoformat(),
            property_type=property_type,
            booking_date=booking_date,
            shift_type=shift_type,
            min_price=min_price,
            max_price=max_price,
            max_occupancy=max_occupancy
        )
        
        # Create a temporary prompt with the formatted system message
        temp_prompt = ChatPromptTemplate(
            [
                ("system", formatted_system_prompt),
                MessagesPlaceholder(variable_name='messages'),
            ]
        )
        
        # Create a temporary agent with the formatted prompt
        temp_agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            state_modifier=temp_prompt
        )
        
        response = temp_agent.invoke({
            "messages": messages,
        })
        
        db.close()
        print("Agent response:", response)
        return response["messages"][-1].content
