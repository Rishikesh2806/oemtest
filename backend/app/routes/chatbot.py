"""
Chatbot Service - AI-powered chatbot using Gemini 3 Flash
Handles FAQs, manufacturing queries, RFQ assistance, and customer support
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import os
import logging
from dotenv import load_dotenv

load_dotenv()

from emergentintegrations.llm.chat import LlmChat, UserMessage
from app.database import db
from app.routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

# System prompt for OEMLinker chatbot
SYSTEM_PROMPT = """You are OEMBot, the friendly AI assistant for OEMLinker - an AI-powered manufacturing marketplace that connects OEM buyers with trusted vendors.

Your personality: Friendly, helpful, conversational, and knowledgeable about manufacturing.

What you can help with:
1. **Platform FAQs**: How OEMLinker works, pricing, features, getting started
2. **Manufacturing Queries**: Materials (metals, plastics, composites), processes (CNC, casting, forging), tolerances, surface finishes
3. **RFQ Assistance**: How to create RFQs, upload drawings, set requirements, get quotes
4. **Vendor Matching**: How the AI matching algorithm works, vendor selection criteria
5. **Order Process**: Quote comparison, order placement, inspections, delivery
6. **Customer Support**: Account issues, technical help, general inquiries

Key OEMLinker Features to mention when relevant:
- AI-powered drawing analysis (extracts specs from CAD files automatically)
- Smart vendor matching based on capabilities, capacity, location
- NDA protection for sensitive drawings
- Third-party inspection system for quality assurance
- Real-time quote comparison tools
- Item-wise and partial quoting options

Contact Information:
- Email: support@oemlinker.com
- WhatsApp: +91-9831509919
- Address: 6th Floor, 4 Lyons Range, Kolkata 700 001, India

Keep responses concise but helpful. Use emojis occasionally to be friendly 😊. If you don't know something specific about a user's order or account, suggest they contact support or check their dashboard."""


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(chat_message: ChatMessage, user: Optional[dict] = None):
    """Send a message to the OEMLinker chatbot"""
    try:
        # Generate or use existing session ID
        session_id = chat_message.session_id or f"chat_{uuid.uuid4().hex[:12]}"
        
        # Get API key
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Chatbot service not configured")
        
        # Get chat history for context
        history = await db.chat_history.find(
            {"session_id": session_id}
        ).sort("created_at", 1).to_list(20)
        
        # Build context from history
        context_messages = []
        for h in history[-10:]:  # Last 10 messages for context
            context_messages.append(f"User: {h.get('user_message', '')}")
            context_messages.append(f"Assistant: {h.get('bot_response', '')}")
        
        # Add user context if logged in
        user_context = ""
        if user:
            user_context = f"\n\nCurrent user: {user.get('name', 'Guest')} ({user.get('role', 'visitor')})"
            if user.get('role') == 'vendor':
                vendor = await db.vendors.find_one({"user_id": user["user_id"]}, {"_id": 0, "company_name": 1})
                if vendor:
                    user_context += f" from {vendor.get('company_name', 'their company')}"
        
        # Create enhanced system message with context
        enhanced_system = SYSTEM_PROMPT + user_context
        if context_messages:
            enhanced_system += f"\n\nRecent conversation:\n" + "\n".join(context_messages[-6:])
        
        # Initialize chat with Gemini 3 Flash
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=enhanced_system
        ).with_model("gemini", "gemini-3-flash-preview")
        
        # Send message and get response
        user_msg = UserMessage(text=chat_message.message)
        response = await chat.send_message(user_msg)
        
        # Store in chat history
        chat_doc = {
            "chat_id": f"msg_{uuid.uuid4().hex[:12]}",
            "session_id": session_id,
            "user_id": user.get("user_id") if user else None,
            "user_message": chat_message.message,
            "bot_response": response,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.chat_history.insert_one(chat_doc)
        
        logger.info(f"Chat response generated for session {session_id}")
        
        return ChatResponse(response=response, session_id=session_id)
        
    except Exception as e:
        logger.error(f"Chatbot error: {str(e)}")
        # Return a friendly fallback message
        return ChatResponse(
            response="I'm having a little trouble right now 😅 Please try again in a moment, or reach out to our team at support@oemlinker.com or WhatsApp +91-9831509919 for immediate assistance!",
            session_id=chat_message.session_id or f"chat_{uuid.uuid4().hex[:12]}"
        )


@router.post("/chat/guest", response_model=ChatResponse)
async def chat_with_bot_guest(chat_message: ChatMessage):
    """Chat endpoint for non-logged-in users"""
    return await chat_with_bot(chat_message, user=None)


@router.post("/chat/user", response_model=ChatResponse)
async def chat_with_bot_user(chat_message: ChatMessage, user: dict = Depends(get_current_user)):
    """Chat endpoint for logged-in users with context"""
    return await chat_with_bot(chat_message, user=user)


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 50):
    """Get chat history for a session"""
    history = await db.chat_history.find(
        {"session_id": session_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(limit)
    
    return {"session_id": session_id, "messages": history}


@router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear chat history for a session"""
    result = await db.chat_history.delete_many({"session_id": session_id})
    return {"message": f"Cleared {result.deleted_count} messages", "session_id": session_id}
