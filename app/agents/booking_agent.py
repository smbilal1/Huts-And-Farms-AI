from datetime import date
from xml.parsers.expat import model
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import create_react_agent
from datetime import date
from app.database import SessionLocal
from app.models import Session, Message
from langchain_google_genai import ChatGoogleGenerativeAI
import google.genai as genai
from sqlalchemy import text
from typing import List, Tuple, Optional, Dict
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from app.core.config import settings
import tiktoken  # For token counting



client = genai.Client(api_key=settings.GOOGLE_API_KEY)

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

🎯 **Required Tools Usage**
- Always run `check_message_relevance()` before processing queries  
- Always use `property_id` when calling tools, resolve names first if needed  

---

**Response Templates:**  
- Date Confirmation: "Do you mean [extracted_date] ([day_name])? Please confirm."  
- Authentication needed: "To view booking details, we first need to verify your contact."  

Use chat history for context and continuity. Kindly tell me, how can I help you today? 🙏
"""

from sqlalchemy import desc

def get_chat_history_normal(user_id: str):
    with SessionLocal() as db:
        
        history = (
            db.query(Message)
            .filter(Message.user_id == user_id)
            .order_by(desc(Message.timestamp))
            .limit(30)
            .all()
        )
        # reverse the order to show oldest first (chat style)
        return [msg.content for msg in reversed(history)]


class BookingToolAgent:
    def __init__(self):
        self.tools = [
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
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite-preview-09-2025", 
            temperature=0,
            google_api_key=settings.GOOGLE_API_KEY
        )

        self.prompt = ChatPromptTemplate(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name='messages'),
            ]
        )

        self.agent = create_react_agent(
            self.llm,
            self.tools,
            state_modifier=self.prompt
        )
        
        # Initialize token encoder for local counting
        try:
            # Use GPT-4 tokenizer as approximation (closest to Gemini)
            self.token_encoder = tiktoken.encoding_for_model("gpt-4")
        except:
            # Fallback to cl100k_base encoding
            self.token_encoder = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens_local(self, text: str) -> int:
        """
        Count tokens using tiktoken library for comparison with Gemini's counts.
        Note: This is an approximation since Gemini uses its own tokenizer.
        """
        try:
            if not text:
                return 0
            return len(self.token_encoder.encode(text))
        except Exception as e:
            print(f"[❌] Local token counting failed: {e}")
            # Fallback: rough estimation (1 token ≈ 4 characters)
            return len(text) // 4
    
    def estimate_prompt_tokens(self, formatted_system_prompt: str, messages: list, tools: list, chat_history: list) -> dict:
        """
        Estimate total input tokens for the prompt using local tokenizer.
        """
        try:
            # Count system prompt tokens
            system_tokens = self.count_tokens_local(formatted_system_prompt)
            
            # Count message history tokens (more accurate)
            message_tokens = 0
            
            # Count raw chat history tokens
            chat_history_text = ""
            for msg in chat_history:
                chat_history_text += msg + "\n"
            chat_history_tokens = self.count_tokens_local(chat_history_text)
            
            # Count formatted messages tokens
            formatted_messages_text = ""
            for role, content in messages:
                formatted_messages_text += f"{role}: {content}\n"
            formatted_messages_tokens = self.count_tokens_local(formatted_messages_text)
            
            # Use the higher count (formatted messages usually more accurate)
            message_tokens = max(chat_history_tokens, formatted_messages_tokens)
            
            # Count tool definition tokens (more realistic representation)
            tools_text = ""
            for tool in tools:
                # Get tool name and docstring
                tool_name = getattr(tool, 'name', str(tool))
                tool_doc = getattr(tool, '__doc__', '') or getattr(tool, 'description', '')
                
                # Simulate JSON schema structure that LangGraph sends
                tool_schema = f"""{{
    "name": "{tool_name}",
    "description": "{tool_doc}",
    "parameters": {{
        "type": "object",
        "properties": {{...}},
        "required": [...]
    }}
}}"""
                tools_text += tool_schema + "\n"
            
            # Also add the raw string representation for comparison
            tools_raw = str(tools)
            tools_tokens_detailed = self.count_tokens_local(tools_text)
            tools_tokens_raw = self.count_tokens_local(tools_raw)
            
            # Use the higher estimate (more conservative)
            tools_tokens = max(tools_tokens_detailed, tools_tokens_raw)
            
            # Add overhead for JSON formatting, role markers, etc.
            base_tokens = system_tokens + message_tokens + tools_tokens
            formatting_overhead = int(base_tokens * 0.15)  # Increased to 15% for more accuracy
            
            total_estimated = base_tokens + formatting_overhead
            
            return {
                "system_prompt": system_tokens,
                "chat_history_raw": chat_history_tokens,
                "messages_formatted": formatted_messages_tokens,
                "messages_used": message_tokens,
                "tools": tools_tokens,
                "tools_detailed": tools_tokens_detailed,
                "tools_raw": tools_tokens_raw,
                "formatting_overhead": formatting_overhead,
                "total_estimated": total_estimated,
                "breakdown": {
                    "chat_history_count": len(chat_history),
                    "formatted_messages_count": len(messages),
                    "tools_count": len(tools)
                }
            }
        except Exception as e:
            print(f"[❌] Prompt token estimation failed: {e}")
            return {
                "system_prompt": 0,
                "chat_history_raw": 0,
                "messages_formatted": 0,
                "messages_used": 0,
                "tools": 0,
                "formatting_overhead": 0,
                "total_estimated": 0,
                "breakdown": {"chat_history_count": 0, "formatted_messages_count": 0, "tools_count": 0}
            }

  
    def get_embedding(self,text: str, task_type: str = "retrieval_document") -> List[float]:
        """
        Generate an embedding for the given text using Google's Gemini embedding model.

        Args:
            text (str): The text to embed.
            task_type (str): Either "retrieval_document" or "retrieval_query".

        Returns:
            List[float]: A list of embedding floats (3072 dimensions).
        """
        try:
            response = client.models.embed_content(
                model="models/gemini-embedding-001",
                content=text,
                task_type=task_type,
            )
            return response.embedding
        except Exception as e:
            print(f"[❌] Embedding generation failed: {e}")
            return []

    def get_response(self, incoming_text: str, session_id: str, whatsapp_message_id: Optional[str]= None):
        db = SessionLocal()
        session = db.query(Session).filter_by(id=session_id).first()

        # --- Save user message ---
        user_id = session.user.user_id
        
        chat_history = []
        chat_history = get_chat_history_normal(user_id=user_id)
        print(f"Chat history: {chat_history}")

        if incoming_text != "Image received run process_payment_screenshot":
            db.add(Message(
                user_id=user_id,
                sender="user",
                content=incoming_text,
                whatsapp_message_id = whatsapp_message_id,
                timestamp=datetime.utcnow()
            ))
            db.commit()

        cnic = session.user.cnic if session else "None"
        name = session.user.name if session else "None"
        client_email = session.user.email if session else "unauthenticated"
        property_type = session.property_type if session else "None"
        booking_date = session.booking_date if session else "None"
        shift_type = session.shift_type if session else "None"
        min_price = session.min_price if session else "None"
        max_price = session.max_price if session else "None"
        max_occupancy = session.max_occupancy if session else "None"
        print(f"client email : {client_email}")
        db.close()
        print(incoming_text)
        # Run agent with context
        messages = []
        for msg in chat_history:
            if msg.startswith("User:"):
                messages.append(("human", msg[5:]))
            elif msg.startswith("Assistant:"):
                messages.append(("assistant", msg[10:]))
        
        # Add current message
        messages.append(("human", incoming_text))
        
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
            self.llm,
            self.tools,
            state_modifier=temp_prompt
        )
        
        # Print agent configuration details
        print(f"\n🤖 AGENT CONFIGURATION:")
        print("─" * 60)
        print(f"   Model: {self.llm.model}")
        print(f"   Temperature: {self.llm.temperature}")
        print(f"   Tools count: {len(self.tools)}")
        print(f"   System prompt length: {len(formatted_system_prompt)} chars")
        print(f"   Agent type: {type(temp_agent).__name__}")
        print("─" * 60)
        
        response = temp_agent.invoke({
            "messages": messages,
        })
        
        # Print what's actually being sent to the agent
        print("\n" + "="*80)
        print("📤 ACTUAL DATA SENT TO AGENT")
        print("="*80)
        
        print(f"\n🔧 SYSTEM PROMPT ({len(formatted_system_prompt)} chars):")
        print("─" * 60)
        print(formatted_system_prompt[:500] + "..." if len(formatted_system_prompt) > 500 else formatted_system_prompt)
        print("─" * 60)
        
        print(f"\n💬 MESSAGES SENT ({len(messages)} messages):")
        print("─" * 60)
        for i, (role, content) in enumerate(messages):
            content_preview = content[:100] + "..." if len(content) > 100 else content
            print(f"   {i+1}. {role}: {content_preview}")
        print("─" * 60)
        
        print(f"\n🔧 TOOLS SENT ({len(self.tools)} tools):")
        print("─" * 60)
        for i, tool in enumerate(self.tools):
            tool_name = getattr(tool, 'name', str(tool))
            tool_doc = getattr(tool, '__doc__', '') or getattr(tool, 'description', '')
            doc_preview = tool_doc[:80] + "..." if len(tool_doc) > 80 else tool_doc
            print(f"   {i+1}. {tool_name}: {doc_preview}")
        print("─" * 60)
        
        print(f"\n📊 RAW INVOKE PARAMETERS:")
        print("─" * 60)
        invoke_params = {"messages": messages}
        print(f"   Parameter keys: {list(invoke_params.keys())}")
        print(f"   Messages count: {len(invoke_params['messages'])}")
        print(f"   Total characters in messages: {sum(len(str(msg)) for msg in invoke_params['messages'])}")
        
        # Show the actual message structure that LangChain creates
        print(f"\n📋 LANGCHAIN MESSAGE STRUCTURE:")
        for i, (role, content) in enumerate(messages):
            print(f"   Message {i+1}:")
            print(f"     Role: '{role}'")
            print(f"     Content: '{content[:50]}{'...' if len(content) > 50 else ''}'")
            print(f"     Length: {len(content)} chars")
        print("─" * 60)
        
        # Show tool details
        print(f"\n🔧 DETAILED TOOL INFORMATION:")
        total_tool_chars = 0
        for i, tool in enumerate(self.tools):
            tool_name = getattr(tool, 'name', f'tool_{i}')
            tool_doc = getattr(tool, '__doc__', '') or ''
            tool_str = str(tool)
            tool_chars = len(tool_name) + len(tool_doc) + len(tool_str)
            total_tool_chars += tool_chars
            
            if i < 3:  # Show first 3 tools in detail
                print(f"   Tool {i+1}: {tool_name}")
                print(f"     Doc: {tool_doc[:100]}{'...' if len(tool_doc) > 100 else ''}")
                print(f"     Str: {tool_str[:100]}{'...' if len(tool_str) > 100 else ''}")
                print(f"     Total chars: {tool_chars}")
            elif i == 3:
                print(f"   ... and {len(self.tools) - 3} more tools")
        
        print(f"   Total tool characters: {total_tool_chars}")
        print("─" * 60)
        
        # Estimate tokens for the initial prompt using local tokenizer
        prompt_estimation = self.estimate_prompt_tokens(formatted_system_prompt, messages, self.tools, chat_history)
        
        # Print detailed multi-tool flow
        print("\n" + "="*80)
        print("🤖 AGENT MULTI-TOOL EXECUTION FLOW")
        print(f"🔧 Model: {self.llm.model}")
        print("="*80)
        
        # Print local token estimation for first API call
        print(f"\n🧮 LOCAL TOKEN ESTIMATION (First API Call):")
        print(f"   System Prompt: ~{prompt_estimation['system_prompt']} tokens")
        print(f"   Chat History (raw): ~{prompt_estimation['chat_history_raw']} tokens ({prompt_estimation['breakdown']['chat_history_count']} messages)")
        print(f"   Messages (formatted): ~{prompt_estimation['messages_formatted']} tokens ({prompt_estimation['breakdown']['formatted_messages_count']} messages)")
        print(f"   Messages (used): ~{prompt_estimation['messages_used']} tokens")
        print(f"   Tool Definitions: ~{prompt_estimation['tools']} tokens ({prompt_estimation['breakdown']['tools_count']} tools)")
        print(f"     - Detailed Schema: ~{prompt_estimation['tools_detailed']} tokens")
        print(f"     - Raw String: ~{prompt_estimation['tools_raw']} tokens")
        print(f"     - Used (higher): ~{prompt_estimation['tools']} tokens")
        print(f"   Formatting Overhead: ~{prompt_estimation['formatting_overhead']} tokens (15%)")
        print(f"   📊 Total Estimated: ~{prompt_estimation['total_estimated']} tokens")
        
        # Debug: Show actual content lengths for comparison
        print(f"\n🔍 DEBUG - CONTENT ANALYSIS:")
        print(f"   System Prompt Length: {len(formatted_system_prompt)} characters")
        print(f"   Chat History Length: {sum(len(msg) for msg in chat_history)} characters")
        print(f"   Tools String Length: {len(str(self.tools))} characters")
        print(f"   Estimated Char-to-Token Ratio: {len(formatted_system_prompt) / prompt_estimation['system_prompt']:.2f} chars/token")
        
        for i, message in enumerate(response["messages"]):
            print(f"\n📝 Message {i+1}: {type(message).__name__}")
            
            if hasattr(message, 'content') and message.content:
                content_preview = message.content[:100] + "..." if len(message.content) > 100 else message.content
                print(f"   Content: {content_preview}")
                
                # Add local token count for content
                if message.content:
                    local_tokens = self.count_tokens_local(message.content)
                    print(f"   📏 Local Count: ~{local_tokens} tokens (content only)")
            
            if hasattr(message, 'tool_calls') and message.tool_calls:
                print(f"   🔧 Tool Calls: {len(message.tool_calls)}")
                for tool_call in message.tool_calls:
                    print(f"      - {tool_call['name']}({tool_call['args']})")
            
            if hasattr(message, 'usage_metadata') and message.usage_metadata:
                usage = message.usage_metadata
                input_tokens = usage.get('input_tokens', 0)
                output_tokens = usage.get('output_tokens', 0)
                total_tokens = usage.get('total_tokens', 0)
                
                print(f"   💰 Gemini Count: {input_tokens} in + {output_tokens} out = {total_tokens} total")
                
                # Compare with local estimation for first message
                if i == 1:  # First AIMessage with usage_metadata
                    difference = abs(input_tokens - prompt_estimation['total_estimated'])
                    accuracy = (1 - difference / input_tokens) * 100 if input_tokens > 0 else 0
                    print(f"   🎯 Estimation Accuracy: {accuracy:.1f}% (diff: {difference} tokens)")
                
                if 'input_token_details' in usage and 'cache_read' in usage['input_token_details']:
                    cache_tokens = usage['input_token_details']['cache_read']
                    total_input = usage.get('input_tokens', 0)
                    cache_ratio = (cache_tokens / total_input * 100) if total_input > 0 else 0
                    print(f"   🗄️  Cache: {cache_tokens} tokens ({cache_ratio:.1f}% cached)")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Model Used: {self.llm.model}")
        print(f"   Total Messages: {len(response['messages'])}")
        
        # Count API calls (AIMessages with usage_metadata)
        api_calls = sum(1 for msg in response["messages"] 
                       if hasattr(msg, 'usage_metadata') and msg.usage_metadata)
        print(f"   API Calls Made: {api_calls}")
        
        # Count tool executions (ToolMessages)
        tool_executions = sum(1 for msg in response["messages"] 
                            if type(msg).__name__ == 'ToolMessage')
        print(f"   Tools Executed: {tool_executions}")
        
        # Calculate total tokens
        total_tokens = sum(msg.usage_metadata.get('total_tokens', 0) 
                          for msg in response["messages"] 
                          if hasattr(msg, 'usage_metadata') and msg.usage_metadata)
        print(f"   Total Tokens: {total_tokens}")
        
        # Calculate total cost with correct pricing
        input_tokens = sum(msg.usage_metadata.get('input_tokens', 0) 
                          for msg in response["messages"] 
                          if hasattr(msg, 'usage_metadata') and msg.usage_metadata)
        output_tokens = sum(msg.usage_metadata.get('output_tokens', 0) 
                           for msg in response["messages"] 
                           if hasattr(msg, 'usage_metadata') and msg.usage_metadata)
        
        # Correct pricing: Input $0.10/1M tokens, Output $0.40/1M tokens
        input_cost = (input_tokens * 0.10) / 1000000
        output_cost = (output_tokens * 0.40) / 1000000
        total_cost = input_cost + output_cost
        
        print(f"   Input Cost: ${input_cost:.6f} ({input_tokens} tokens × $0.10/1M)")
        print(f"   Output Cost: ${output_cost:.6f} ({output_tokens} tokens × $0.40/1M)")
        print(f"   Total Cost: ${total_cost:.6f}")
        
        # Token validation - cross-check calculations
        print(f"\n🔍 TOKEN VALIDATION:")
        calculated_total = input_tokens + output_tokens
        print(f"   Calculated Total: {input_tokens} + {output_tokens} = {calculated_total}")
        print(f"   Reported Total: {total_tokens}")
        
        if calculated_total == total_tokens:
            print(f"   ✅ Token calculation VERIFIED - Numbers match!")
        else:
            print(f"   ⚠️  Token mismatch detected!")
            print(f"   Difference: {abs(calculated_total - total_tokens)} tokens")
        
        # Cache validation
        total_cache_tokens = sum(
            msg.usage_metadata.get('input_token_details', {}).get('cache_read', 0)
            for msg in response["messages"] 
            if hasattr(msg, 'usage_metadata') and msg.usage_metadata
        )
        cache_percentage = (total_cache_tokens / input_tokens * 100) if input_tokens > 0 else 0
        print(f"   Total Cached: {total_cache_tokens} tokens ({cache_percentage:.1f}% of input)")
        
        # Individual message validation
        print(f"\n📋 PER-MESSAGE BREAKDOWN:")
        for i, msg in enumerate(response["messages"]):
            if hasattr(msg, 'usage_metadata') and msg.usage_metadata:
                usage = msg.usage_metadata
                msg_input = usage.get('input_tokens', 0)
                msg_output = usage.get('output_tokens', 0)
                msg_total = usage.get('total_tokens', 0)
                msg_calculated = msg_input + msg_output
                
                status = "✅" if msg_calculated == msg_total else "⚠️"
                print(f"   Message {i+1}: {msg_input}+{msg_output}={msg_calculated} (reported: {msg_total}) {status}")
        
        print("="*80)
        
        return response["messages"][-1].content
