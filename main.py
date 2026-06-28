import sys
import os
import logging
import traceback
import asyncio
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
logging.getLogger("pymongo").setLevel(logging.WARNING)

# Ensure module path works when running via uvicorn
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# FastAPI application
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

# Groq client
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable not set")
groq_client = Groq(api_key=GROQ_API_KEY)

# Admin API Key for authentication
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-secret-key-123")
api_key_header = APIKeyHeader(name="X-Admin-API-Key", auto_error=False)

async def verify_admin_key(api_key: str = Depends(api_key_header)):
    """Verify admin API key for protected endpoints."""
    if api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key"
        )
    return api_key

# MongoDB connections
from pymongo import MongoClient
import motor.motor_asyncio

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI environment variable not set")

# Synchronous client for quick reads/writes
sync_mongo_client = MongoClient(MONGODB_URI)

# Asynchronous client for async endpoints
async_mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)

# Collections
sync_users_collection = sync_mongo_client["welfarebot"]["users"]
sync_schemes_collection = sync_mongo_client["welfarebot"]["schemes"]
conversations_collection = async_mongo_client["welfarebot"]["conversations"]

# Build LangGraph
from agent.graph import build_graph
from chromadb import PersistentClient

chroma_client = PersistentClient(path="./chroma_storage")

welfare_graph = build_graph(groq_client, sync_users_collection, sync_schemes_collection)

# Scraper + scheduler (moved to top so they're defined before any endpoint uses them)
from scraper.manager import run_scraper
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(run_scraper, "interval", days=3, id="scraper_job")
scheduler.start()

# FastAPI app instance
app = FastAPI(title="WelfareBot Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    show_form_choice: Optional[bool] = None
    clear_session: Optional[bool] = None
    chips: Optional[List[str]] = None


class SubmitProfileRequest(BaseModel):
    session_id: str
    name: str
    language_preference: str
    state: str
    occupation: str
    caste_category: str
    gender: str
    age: str
    income_bracket: str
    aadhaar: Optional[str] = ""


# Helper function to generate chips dynamically
def generate_chips(onboarding_step: str, user_doc: dict, intent: str = None, schemes: list = None, message: str = "") -> List[str]:
    """Generate suggestion chips based on conversation state."""
    chips = []
    
    # Check intent first for scheme_query and FAQ
    if intent == "scheme_query" and schemes:
        # Add scheme names as chips
        for scheme in schemes[:5]:
            chips.append(scheme.get("name", "Unknown Scheme"))
        chips.append("Ask Something Else")
        # If user selected a scheme (message matches scheme name), add Apply Now
        if schemes and any(s.get("name", "").lower() in message.lower() for s in schemes):
            chips.append("Apply Now")
    elif intent == "faq":
        chips.extend(["Find My Schemes", "Ask Something Else"])
    # Then check onboarding steps
    elif onboarding_step == "name":
        chips.extend(["English", "हिंदी", "తెలుగు", "தமிழ்", "ಕನ్नड"])
    elif onboarding_step == "language":
        chips.extend(["📝 Fill Form", "💬 Chat instead"])
    elif onboarding_step == "details":
        # During profile collection
        if not user_doc.get("state"):
            chips.extend(["Andhra Pradesh", "Telangana", "Delhi", "Maharashtra", "Tamil Nadu"])
        elif not user_doc.get("occupation"):
            chips.extend(["Student", "Farmer", "Daily Wage Worker", "Government Employee", "Business"])
        elif not user_doc.get("caste_category"):
            chips.extend(["General", "OBC", "SC", "ST", "EWS"])
        elif not user_doc.get("gender"):
            chips.extend(["Male", "Female", "Other"])
        elif not user_doc.get("age"):
            chips.extend(["18-25", "26-35", "36-50", "50+"])
        elif not user_doc.get("income_bracket"):
            chips.extend(["Below 1 Lakh", "1-2.5 Lakh", "2.5-5 Lakh", "5-10 Lakh", "Above 10 Lakh"])
    elif onboarding_step == "confirmation":
        chips.extend(["Yes Continue", "Edit Details"])
    
    # Always add Start Over at the end
    chips.append("Start Over")
    
    return chips

# Endpoints
@app.post("/voice-input")
async def voice_input(file: UploadFile = File(...)):
    """Handle voice input - transcribe audio and return text with detected language."""
    try:
        # Read audio file
        audio_data = await file.read()
        
        # Save to temporary file
        temp_path = f"temp_audio_{int(time.time())}.webm"
        with open(temp_path, "wb") as f:
            f.write(audio_data)
        
        from agent.languages import detect_language
        
        # Try to use a simple transcription approach
        # For production, integrate Whisper or similar STT service
        # This is a basic implementation that would need enhancement
        transcribed_text = ""
        
        # Check if we can use a basic transcription library
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            
            # Convert webm to wav if needed (simplified)
            # For now, we'll use a placeholder approach
            transcribed_text = "Voice transcription requires audio format conversion. Please use text input."
        except ImportError:
            transcribed_text = "Speech recognition library not installed. Please install speech_recognition or integrate a cloud STT service."
        
        # Detect language from transcribed text
        detected_lang = detect_language(transcribed_text) if transcribed_text else "en"
        
        # Clean up temp file
        import os
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return {
            "transcribed_text": transcribed_text,
            "detected_language": detected_lang,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Voice input error: {e}")
        return {
            "transcribed_text": "",
            "detected_language": "en",
            "status": "error",
            "error": str(e)
        }

@app.post("/send-reminder")
async def send_reminder(session_id: str = Form(...), message: str = Form(...)):
    """Send an email reminder to a user about schemes or deadlines."""
    try:
        # Get user details
        user_doc = sync_users_collection.find_one({"session_id": session_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user has email
        user_email = user_doc.get("email")
        if not user_email:
            return {
                "status": "error",
                "message": "User email not found. Please provide email in profile."
            }
        
        # For demo purposes, we'll log the email instead of actually sending
        # In production, integrate with SMTP service like SendGrid, AWS SES, etc.
        logger.info(f"EMAIL REMINDER - To: {user_email}, Message: {message}")
        
        return {
            "status": "success",
            "message": f"Reminder queued for {user_email}",
            "email": user_email
        }
    except Exception as e:
        logger.error(f"Send reminder error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/schedule-reminder")
async def schedule_reminder(session_id: str = Form(...), reminder_date: str = Form(...), message: str = Form(...)):
    """Schedule a reminder for a specific date."""
    try:
        # Parse reminder date
        try:
            reminder_dt = datetime.fromisoformat(reminder_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD HH:MM:SS)")
        
        # Get user details
        user_doc = sync_users_collection.find_one({"session_id": session_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Store reminder in database
        reminder_doc = {
            "session_id": session_id,
            "email": user_doc.get("email"),
            "reminder_date": reminder_dt,
            "message": message,
            "sent": False,
            "created_at": datetime.utcnow()
        }
        
        # Create reminders collection if it doesn't exist
        sync_users_collection.database.create_collection("reminders")
        reminders_collection = sync_users_collection.database["reminders"]
        
        reminders_collection.insert_one(reminder_doc)
        
        return {
            "status": "success",
            "message": f"Reminder scheduled for {reminder_date}",
            "reminder_date": reminder_date
        }
    except Exception as e:
        logger.error(f"Schedule reminder error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reminders/{session_id}")
async def get_reminders(session_id: str):
    """Get all reminders for a user."""
    try:
        reminders_collection = sync_users_collection.database["reminders"]
        reminders = list(reminders_collection.find({"session_id": session_id}, {"_id": 0}))
        return {"reminders": reminders}
    except Exception as e:
        logger.error(f"Get reminders error: {e}")
        return {"reminders": []}

# Admin Dashboard Endpoints
@app.get("/admin/users")
async def get_all_users(admin_key: str = Depends(verify_admin_key)):
    """Get all users for admin dashboard."""
    try:
        users = list(sync_users_collection.find({}, {"_id": 0}))
        return {"users": users, "count": len(users)}
    except Exception as e:
        logger.error(f"Get users error: {e}")
        return {"users": [], "count": 0}

@app.get("/admin/conversations")
async def get_all_conversations(limit: int = 100, admin_key: str = Depends(verify_admin_key)):
    """Get all conversations for admin dashboard."""
    try:
        conversations = list(sync_conversations_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
        return {"conversations": conversations, "count": len(conversations)}
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        return {"conversations": [], "count": 0}

@app.get("/admin/analytics")
async def get_analytics(admin_key: str = Depends(verify_admin_key)):
    """Get analytics data for admin dashboard."""
    try:
        # User statistics
        total_users = sync_users_collection.count_documents({})
        completed_onboarding = sync_users_collection.count_documents({"onboarding_step": "complete"})
        
        # Conversation statistics
        total_conversations = sync_conversations_collection.count_documents({})
        
        # Scheme statistics
        total_schemes = sync_schemes_collection.count_documents({})
        
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_users = sync_users_collection.count_documents({"created_at": {"$gte": yesterday}}) if "created_at" in sync_users_collection.find_one() else 0
        recent_conversations = sync_conversations_collection.count_documents({"timestamp": {"$gte": yesterday}})
        
        return {
            "users": {
                "total": total_users,
                "completed_onboarding": completed_onboarding,
                "recent": recent_users
            },
            "conversations": {
                "total": total_conversations,
                "recent": recent_conversations
            },
            "schemes": {
                "total": total_schemes
            }
        }
    except Exception as e:
        logger.error(f"Get analytics error: {e}")
        return {"error": str(e)}

@app.delete("/admin/users/{session_id}")
async def delete_user(session_id: str, admin_key: str = Depends(verify_admin_key)):
    """Delete a user (admin only)."""
    try:
        result = sync_users_collection.delete_one({"session_id": session_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"status": "success", "message": "User deleted"}
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/admin/schemes")
async def add_scheme(scheme: dict, admin_key: str = Depends(verify_admin_key)):
    """Add a new scheme (admin only)."""
    try:
        sync_schemes_collection.insert_one(scheme)
        return {"status": "success", "message": "Scheme added"}
    except Exception as e:
        logger.error(f"Add scheme error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/schemes/{scheme_id}")
async def delete_scheme(scheme_id: str, admin_key: str = Depends(verify_admin_key)):
    """Delete a scheme (admin only)."""
    try:
        result = sync_schemes_collection.delete_one({"_id": scheme_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Scheme not found")
        return {"status": "success", "message": "Scheme deleted"}
    except Exception as e:
        logger.error(f"Delete scheme error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "running", "db": "connected"}


@app.get("/schemes")
async def get_schemes():
    schemes = list(sync_schemes_collection.find({}, {"_id": 0}))
    return {"schemes": schemes}


# Serve React frontend (SPA)
# Mount static files
try:
    app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")
    app.mount("/favicon.ico", StaticFiles(directory="frontend/build"), name="favicon")
except Exception as e:
    logger.warning(f"Could not mount static files (frontend may not be built yet): {e}")

@app.get("/")
async def serve_react():
    try:
        return FileResponse("frontend/build/index.html")
    except Exception as e:
        logger.warning(f"Could not serve index.html (frontend may not be built yet): {e}")
        return {"status": "backend_running", "message": "Frontend not built yet"}

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Catch all routes for React SPA routing"""
    # Don't catch API routes
    if full_path.startswith("api") or full_path.startswith("admin") or full_path.startswith("health"):
        raise HTTPException(status_code=404, detail="Not found")
    try:
        return FileResponse("frontend/build/index.html")
    except Exception as e:
        logger.warning(f"Could not serve index.html (frontend may not be built yet): {e}")
        raise HTTPException(status_code=404, detail="Frontend not built yet")


@app.get("/session")
async def get_session(session_id: str):
    user = sync_users_collection.find_one({"session_id": session_id})
    return {"session_id": session_id, "profile": user or {}}


@app.post("/submit-profile")
async def submit_profile(request: SubmitProfileRequest):
    try:
        profile_dict = request.dict()
        sync_users_collection.update_one(
            {"session_id": request.session_id},
            {"$set": profile_dict},
            upsert=True,
        )

        from agent.eligibility import match_schemes

        schemes = match_schemes(profile_dict, sync_schemes_collection)
        return {"status": "success", "schemes": schemes[:5]}
    except Exception as e:
        return {"error": str(e)}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        session_id = request.session_id
        message = request.message.strip()

        if not message:
            return ChatResponse(reply="Please say something.")

        # Determine onboarding flow
        user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
        onboarding_step = user_doc.get("onboarding_step", "name")
        has_name = user_doc.get("name")

        # ---- Onboarding flow - handle name step directly ----
        if onboarding_step == "name" and not has_name:
            from agent.nodes import extract_first_name
            name = extract_first_name(message)
            sync_users_collection.update_one(
                {"session_id": session_id},
                {"$set": {"name": name, "onboarding_step": "language_preference"}},
                upsert=True,
            )
            reply = f"Hi {name}! 😊\n\nWhich language do you prefer?"
            chips = generate_chips("name", user_doc)
            return ChatResponse(reply=reply, show_form_choice=False, clear_session=False, chips=chips)
        
        # ---- Onboarding flow - handle language step directly ----
        if onboarding_step == "language_preference" and not user_doc.get("language_preference"):
            lang_map = {
                "hindi": "hi", "हिंदी": "hi",
                "telugu": "te", "తెలుగు": "te",
                "tamil": "ta", "தமிழ்": "ta",
                "kannada": "kn", "ಕನ్नड": "kn",
            }
            lower_msg = message.lower()
            lang = "en"
            for key, code in lang_map.items():
                if key in lower_msg:
                    lang = code
                    break
            sync_users_collection.update_one(
                {"session_id": session_id},
                {"$set": {"language_preference": lang, "onboarding_step": "form_chat_choice"}},
                upsert=True,
            )
            reply = "Great! I'm here to help you find welfare schemes that match your profile. Would you like to fill a form with your details or just chat to ask questions?"
            chips = generate_chips("language", user_doc)
            return ChatResponse(reply=reply, show_form_choice=True, clear_session=False, chips=chips)


        # Existing handling for other messages
        state = {
            "session_id": session_id,
            "message": message,
            "onboarding_step": onboarding_step,
            "intent": None,
            "reply": None,
            "show_form_choice": None,
            "clear_session": None,
            "user_profile": user_doc,
            "confirmation_step": user_doc.get("confirmation_step"),
            "editing_field": user_doc.get("editing_field"),
        }

        result = welfare_graph.invoke(state)

        reply = result.get("reply", "Sorry, couldn't process that.")
        show_form_choice = result.get("show_form_choice", False)
        clear_session = result.get("clear_session", False)
        
        # Generate chips based on result state
        result_onboarding_step = result.get("onboarding_step", onboarding_step)
        result_intent = result.get("intent")
        result_schemes = result.get("schemes")
        # Use the updated user_doc for chip generation (after onboarding updates)
        updated_user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
        
        chips = generate_chips(result_onboarding_step, updated_user_doc, result_intent, result_schemes, message)

        await conversations_collection.insert_one({
            "session_id": session_id,
            "user_message": message,
            "bot_reply": reply,
            "intent": result.get("intent"),
            "timestamp": datetime.utcnow(),
        })

        return ChatResponse(
            reply=reply,
            show_form_choice=show_form_choice,
            clear_session=clear_session,
            chips=chips,
        )
    except Exception as e:
        logging.error(f"Chat endpoint error: {e}")
        return ChatResponse(reply=f"Error: {str(e)}")


# Startup diagnostics
print("\n" + "=" * 50)
print("WELFAREBOT BACKEND READY (Groq-only)")
print("=" * 50)
print(f"[OK] Groq client: {groq_client}")
print(f"[OK] MongoDB connected: {sync_mongo_client}")
print(f"[OK] Users collection: {sync_users_collection}")
print(f"[OK] Schemes collection: {sync_schemes_collection}")
print(f"[OK] LangGraph: {welfare_graph}")

# Initialize Chromadb collection for RAG (reuses chroma_client created above)
collection = chroma_client.get_or_create_collection(name="welfare_schemes")
print("=" * 50 + "\n")

# -------------------- API ENDPOINTS --------------------

# Existing staging endpoint
@app.get("/staging")
async def get_staging():
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGODB_URI"))
    db = client.get_default_database()
    cursor = db.staging.find({"status": "pending"}).sort("scraped_at", -1).limit(100)
    return await cursor.to_list(length=100)


# RAG endpoint – simple semantic search over stored schemes
@app.post("/rag")
async def rag_query(query: dict):
    """Accepts JSON {"question": "..."} and returns top matching scheme texts."""
    question = query.get("question", "")
    if not question:
        raise HTTPException(status_code=400, detail="Question required")

    try:
        # Use Groq to get embedding (placeholder: use text as is)
        # For now, perform a naive text match against stored documents
        docs = collection.get(ids=collection.get().ids)
        # Very naive: return first 3 documents
        return {"matches": docs['documents'][:3]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint to manually trigger scraper
@app.post("/scraper/run")
async def trigger_scraper():
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_scraper)
    return {"status": "scraper started", "message": "Check /staging in 1-2 minutes"}