"""
Chatbot Service - AI-powered chatbot using Gemini 3 Flash
Handles FAQs, manufacturing queries, RFQ assistance, and customer support
Includes analytics tracking for popular questions and response quality
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import os
import logging
import re
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

from emergentintegrations.llm.chat import LlmChat, UserMessage
from app.database import db
from app.routes.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

# Question categories for analytics
QUESTION_CATEGORIES = {
    "platform_faq": ["how does", "what is oemlinker", "pricing", "cost", "free", "features", "getting started", "sign up", "register"],
    "manufacturing": ["material", "metal", "plastic", "aluminum", "steel", "cnc", "casting", "forging", "tolerance", "surface finish", "process"],
    "rfq_help": ["rfq", "create rfq", "upload drawing", "cad", "specification", "requirement", "quote request"],
    "vendor_matching": ["vendor", "matching", "find manufacturer", "supplier", "how are vendors", "match algorithm"],
    "order_process": ["order", "quote", "comparison", "inspection", "delivery", "tracking", "payment"],
    "support": ["help", "issue", "problem", "contact", "support", "account", "login", "password"]
}

def categorize_question(question: str) -> str:
    """Categorize a question based on keywords"""
    question_lower = question.lower()
    for category, keywords in QUESTION_CATEGORIES.items():
        if any(keyword in question_lower for keyword in keywords):
            return category
    return "general"

def extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords from text"""
    # Remove common words and extract key terms
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", 
                  "have", "has", "had", "do", "does", "did", "will", "would", "could", 
                  "should", "may", "might", "must", "shall", "can", "need", "dare", 
                  "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by", 
                  "from", "as", "into", "through", "during", "before", "after", "above",
                  "below", "between", "under", "again", "further", "then", "once", "here",
                  "there", "when", "where", "why", "how", "all", "each", "few", "more",
                  "most", "other", "some", "such", "no", "nor", "not", "only", "own",
                  "same", "so", "than", "too", "very", "just", "and", "but", "if", "or",
                  "because", "until", "while", "this", "that", "these", "those", "i", "me",
                  "my", "myself", "we", "our", "you", "your", "he", "him", "she", "her",
                  "it", "its", "they", "them", "what", "which", "who", "whom"}
    
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    keywords = [w for w in words if w not in stop_words]
    return keywords[:10]  # Return top 10 keywords

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
    chat_id: Optional[str] = None


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
            enhanced_system += "\n\nRecent conversation:\n" + "\n".join(context_messages[-6:])
        
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
            "category": categorize_question(chat_message.message),
            "keywords": extract_keywords(chat_message.message),
            "response_length": len(response),
            "feedback": None,  # Will be updated via feedback endpoint
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.chat_history.insert_one(chat_doc)
        
        logger.info(f"Chat response generated for session {session_id}")
        
        return ChatResponse(response=response, session_id=session_id, chat_id=chat_doc["chat_id"])
        
    except Exception as e:
        logger.error(f"Chatbot error: {str(e)}")
        # Return a friendly fallback message
        return ChatResponse(
            response="I'm having a little trouble right now 😅 Please try again in a moment, or reach out to our team at support@oemlinker.com or WhatsApp +91-9831509919 for immediate assistance!",
            session_id=chat_message.session_id or f"chat_{uuid.uuid4().hex[:12]}",
            chat_id=None
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


# ============== FEEDBACK ENDPOINTS ==============

class FeedbackRequest(BaseModel):
    chat_id: str
    rating: int  # 1-5 stars or thumbs up/down (1 or 5)
    comment: Optional[str] = None


@router.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Submit feedback for a chat response"""
    if feedback.rating < 1 or feedback.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    result = await db.chat_history.update_one(
        {"chat_id": feedback.chat_id},
        {"$set": {
            "feedback": {
                "rating": feedback.rating,
                "comment": feedback.comment,
                "submitted_at": datetime.now(timezone.utc).isoformat()
            }
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Chat message not found")
    
    logger.info(f"Feedback submitted for chat {feedback.chat_id}: {feedback.rating}/5")
    return {"success": True, "message": "Thank you for your feedback!"}


# ============== ANALYTICS ENDPOINTS (Admin) ==============

@router.get("/analytics/summary")
async def get_chat_analytics_summary(days: int = 30, user: dict = Depends(get_current_user)):
    """Get summary analytics for chatbot (Admin only)"""
    if user.get("role") not in ["admin", "staff"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Calculate date range
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get all chats in date range
    chats = await db.chat_history.find(
        {"created_at": {"$gte": start_date}},
        {"_id": 0}
    ).to_list(10000)
    
    total_chats = len(chats)
    
    # Calculate metrics
    categories = Counter(chat.get("category", "general") for chat in chats)
    
    # Get feedback stats
    feedbacks = [chat.get("feedback") for chat in chats if chat.get("feedback")]
    avg_rating = sum(f["rating"] for f in feedbacks) / len(feedbacks) if feedbacks else 0
    positive_feedback = sum(1 for f in feedbacks if f["rating"] >= 4)
    negative_feedback = sum(1 for f in feedbacks if f["rating"] <= 2)
    
    # Get keyword frequency
    all_keywords = []
    for chat in chats:
        all_keywords.extend(chat.get("keywords", []))
    top_keywords = Counter(all_keywords).most_common(20)
    
    # Get popular questions (sample of actual questions)
    popular_questions = []
    question_counts = Counter(chat.get("user_message", "").lower()[:100] for chat in chats)
    for q, count in question_counts.most_common(10):
        if len(q) > 10:  # Filter out very short messages
            popular_questions.append({"question": q, "count": count})
    
    # Unique sessions
    unique_sessions = len(set(chat.get("session_id") for chat in chats))
    
    # Chats per day
    chats_by_date = Counter(chat.get("created_at", "")[:10] for chat in chats)
    daily_chats = [{"date": date, "count": count} for date, count in sorted(chats_by_date.items())[-30:]]
    
    # Response time analysis (avg response length as proxy)
    avg_response_length = sum(chat.get("response_length", 0) for chat in chats) / total_chats if total_chats else 0
    
    return {
        "period_days": days,
        "total_conversations": total_chats,
        "unique_sessions": unique_sessions,
        "avg_messages_per_session": round(total_chats / unique_sessions, 1) if unique_sessions else 0,
        "categories": dict(categories),
        "feedback": {
            "total_feedback": len(feedbacks),
            "average_rating": round(avg_rating, 2),
            "positive": positive_feedback,
            "negative": negative_feedback,
            "satisfaction_rate": round((positive_feedback / len(feedbacks) * 100) if feedbacks else 0, 1)
        },
        "top_keywords": top_keywords,
        "popular_questions": popular_questions,
        "daily_activity": daily_chats,
        "avg_response_length": round(avg_response_length)
    }


@router.get("/analytics/questions")
async def get_popular_questions(
    days: int = 30, 
    category: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """Get list of popular questions with details (Admin only)"""
    if user.get("role") not in ["admin", "staff"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    query = {"created_at": {"$gte": start_date}}
    if category:
        query["category"] = category
    
    chats = await db.chat_history.find(
        query,
        {"_id": 0, "chat_id": 1, "user_message": 1, "bot_response": 1, "category": 1, 
         "keywords": 1, "feedback": 1, "created_at": 1, "user_id": 1}
    ).sort("created_at", -1).to_list(limit)
    
    return {"questions": chats, "total": len(chats), "category": category}


@router.get("/analytics/feedback")
async def get_feedback_details(
    days: int = 30,
    rating_filter: Optional[int] = None,
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    """Get detailed feedback with questions and responses (Admin only)"""
    if user.get("role") not in ["admin", "staff"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    query = {
        "created_at": {"$gte": start_date},
        "feedback": {"$ne": None}
    }
    
    if rating_filter:
        query["feedback.rating"] = rating_filter
    
    feedbacks = await db.chat_history.find(
        query,
        {"_id": 0}
    ).sort("feedback.submitted_at", -1).to_list(limit)
    
    return {
        "feedbacks": feedbacks,
        "total": len(feedbacks),
        "rating_filter": rating_filter
    }


@router.get("/analytics/categories")
async def get_category_breakdown(days: int = 30, user: dict = Depends(get_current_user)):
    """Get detailed breakdown by question category (Admin only)"""
    if user.get("role") not in ["admin", "staff"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    chats = await db.chat_history.find(
        {"created_at": {"$gte": start_date}},
        {"_id": 0, "category": 1, "feedback": 1}
    ).to_list(10000)
    
    # Group by category with feedback stats
    category_stats = {}
    for chat in chats:
        cat = chat.get("category", "general")
        if cat not in category_stats:
            category_stats[cat] = {"count": 0, "ratings": [], "positive": 0, "negative": 0}
        
        category_stats[cat]["count"] += 1
        
        if chat.get("feedback"):
            rating = chat["feedback"]["rating"]
            category_stats[cat]["ratings"].append(rating)
            if rating >= 4:
                category_stats[cat]["positive"] += 1
            elif rating <= 2:
                category_stats[cat]["negative"] += 1
    
    # Calculate averages
    result = []
    for cat, stats in category_stats.items():
        avg_rating = sum(stats["ratings"]) / len(stats["ratings"]) if stats["ratings"] else 0
        result.append({
            "category": cat,
            "total_questions": stats["count"],
            "feedback_count": len(stats["ratings"]),
            "avg_rating": round(avg_rating, 2),
            "positive_feedback": stats["positive"],
            "negative_feedback": stats["negative"]
        })
    
    # Sort by count descending
    result.sort(key=lambda x: x["total_questions"], reverse=True)
    
    return {"categories": result, "period_days": days}

