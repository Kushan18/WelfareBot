from fastapi import APIRouter, HTTPException
import logging
from datetime import datetime
from models.chat import ChatRequest, ChatResponse, SubmitProfileRequest
from core.db import users_collection, schemes_collection, conversations_collection

# Import graph builder and create graph
from agent.graph import build_graph
from agent.nodes import groq_client

# Initialize welfare_graph if resources are available
try:
    if users_collection is not None and schemes_collection is not None:
        welfare_graph = build_graph(groq_client, users_collection, schemes_collection)
    else:
        welfare_graph = None  # Gracefully handle missing resources
except ImportError:
    welfare_graph = None  # Gracefully handle missing graph during startup

router = APIRouter()

# Session retrieval
@router.get("/session")
async def get_session(session_id: str):
    if users_collection is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    user = users_collection.find_one({"session_id": session_id})
    return {"session_id": session_id, "profile": user or {}}

# Profile submission – matches models/chat SubmitProfileRequest
@router.post("/submit-profile")
async def submit_profile(request: SubmitProfileRequest):
    try:
        profile_dict = request.dict()
        if users_collection is None:
            raise HTTPException(status_code=500, detail="Database not initialized")
        users_collection.update_one({"session_id": request.session_id}, {"$set": profile_dict}, upsert=True)
        from agent.eligibility import match_schemes
        schemes = match_schemes(profile_dict, schemes_collection)[:8]
        users_collection.update_one({"session_id": request.session_id}, {"$set": {
            "onboarding_step": "ready",
            "last_schemes": [s.get("name") for s in schemes],
            "selected_scheme": None,
        }})
        clean = [{k: v for k, v in s.items() if k != "_id"} for s in schemes]
        return {"status": "success", "schemes": clean}
    except Exception as e:
        logging.error(f"Submit profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Chat endpoint – delegates to agent conversation logic
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        session_id = request.session_id
        message = request.message.strip()
        if not message:
            return ChatResponse(reply="Please say something.", chips=["Start Over"])
        from agent.conversation import handle_turn
        if welfare_graph is None:
            # Return a simple fallback response when the graph is unavailable.
            return ChatResponse(reply="Graph not available. Please try again later.", chips=[])
        result = handle_turn(session_id, message, users_collection, schemes_collection, welfare_graph)
        if conversations_collection is not None:
            conversations_collection.insert_one({
                "session_id": session_id,
                "user_message": message,
                "bot_reply": result.get("reply"),
                "intent": result.get("intent"),
                "timestamp": datetime.utcnow(),
            })
        return ChatResponse(
            reply=result.get("reply", ""),
            chips=result.get("chips", []),
            show_form_choice=result.get("show_form_choice", False),
            open_form=result.get("open_form", False),
            clear_session=result.get("clear_session", False),
            intent=result.get("intent"),
        )
    except Exception as e:
        logging.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
