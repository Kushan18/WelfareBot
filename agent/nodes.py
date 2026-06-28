import os
import re
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from pymongo import MongoClient
import motor.motor_asyncio
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable not set")
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI environment variable not set")

# Initialize Groq client (will be set by main.py)
groq_client = None

# Initialize MongoDB clients (will be set by main.py)
sync_users_collection = None
sync_schemes_collection = None
conversations_collection = None

# Set up MongoDB connection if running standalone
if not groq_client:
    from pymongo import MongoClient
    import motor.motor_asyncio
    sync_mongo_client = MongoClient(MONGODB_URI)
    async_mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
    sync_users_collection = sync_mongo_client["welfarebot"]["users"]
    sync_schemes_collection = sync_mongo_client["welfarebot"]["schemes"]
    conversations_collection = async_mongo_client["welfarebot"]["conversations"]
    groq_client = Groq(api_key=GROQ_API_KEY)

# Logging
logger = logging.getLogger(__name__)

# ---------- Constants ----------
REQUIRED_FIELDS = [
    "name",
    "language_preference",
    "state",
    "occupation",
    "caste_category",
    "gender",
    "age",
    "income_bracket",
    "land_size",
    "email",
]

SCHEME_KEYWORDS = [
    "scheme",
    "eligible",
    "scholarship",
    "benefit",
    "welfare",
    "apply",
    "government",
    "subsidy",
    "yojana",
    "assistance",
]

# ---------- Helper Functions ----------
def extract_first_name(text: str) -> str:
    """Extract a first name using regex patterns.
    Returns capitalised name or a fallback.
    """
    patterns = [
        r"my\s+name\s+is\s+(\w+)",
        r"i\s+am\s+(\w+)",
        r"i['']?m\s+(\w+)",
        r"call\s+me\s+(\w+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).capitalize()
    # fallback – first word
    words = text.strip().split()
    return words[0].capitalize() if words else "Friend"

def safe_groq_chat(messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
    """Call Groq chat completion with retries and timeout.
    Returns the response text or an empty string on failure.
    """
    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=temperature,
                timeout=10,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq chat error (attempt {attempt}): {e}")
            if attempt == max_retries:
                return ""
    return ""

def calculate_confidence(message: str, intent: str, user_profile: dict) -> float:
    """Calculate confidence score for a query based on various factors.
    Returns a float between 0.0 and 1.0.
    """
    score = 0.5  # Base confidence
    
    # Boost confidence for clear intent
    if intent == "scheme_query":
        # Check if profile is complete
        required_fields = ["state", "occupation", "caste_category", "gender", "age", "income_bracket"]
        profile_complete = all(user_profile.get(f) for f in required_fields)
        if profile_complete:
            score += 0.3
        else:
            score -= 0.2
    
    # Boost for longer, more detailed messages
    if len(message) > 20:
        score += 0.1
    if len(message) > 50:
        score += 0.1
    
    # Boost for scheme-related keywords
    scheme_keywords = ["scheme", "benefit", "subsidy", "government", "apply", "eligibility"]
    if any(kw in message.lower() for kw in scheme_keywords):
        score += 0.2
    
    # Reduce confidence for very short messages
    if len(message) < 5:
        score -= 0.3
    
    # Ensure score is between 0 and 1
    return max(0.0, min(1.0, score))

# ---------- Intent Detection & Handlers ----------
def detect_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Determine user intent for routing.
    Updates `state["intent"]`.
    """
    message = state.get("message", "").lower()
    user_doc = state.get("user_profile", {})
    current_step = user_doc.get("onboarding_step", "name")
    has_name = user_doc.get("name")
    
    # DEBUG LOG
    logger.info(f"DEBUG detect_intent: current_step={current_step}, has_name={has_name}, message={message[:50]}")
    
    # If still in onboarding or no name yet, ALWAYS route to onboarding handler
    if current_step in ["name", "language_preference", "continue_confirm", "form_chat_choice", "state", "occupation", "caste_category", "gender", "age", "income_bracket", "confirmation"] or not has_name:
        intent = "onboarding"
        logger.info(f"Routing to onboarding (current_step: {current_step}, has_name: {bool(has_name)})")
    # Scheme‑related keywords
    elif any(kw in message for kw in SCHEME_KEYWORDS):
        profile_complete = all(user_doc.get(f) for f in REQUIRED_FIELDS)
        if not profile_complete:
            intent = "onboarding"
        else:
            intent = "scheme_query"
    else:
        intent = "faq"
    
    state["intent"] = intent
    logger.info(f"detect_intent -> {intent} (onboarding_step: {current_step})")
    return state

def handle_onboarding(state: Dict[str, Any]) -> Dict[str, Any]:
    """Collect missing profile fields step‑by‑step.
    Uses `extract_first_name` for the first step.
    """
    session_id = state["session_id"]
    message = state["message"].strip()
    # Load current profile (or empty dict)
    user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
    current_step = user_doc.get("onboarding_step", "name")

    # Helper to persist step
    def update_profile(updates: Dict[str, Any]):
        sync_users_collection.update_one(
            {"session_id": session_id},
            {"$set": updates},
            upsert=True,
        )

    # STEP 1 – name extraction
    if current_step == "name":
        name = extract_first_name(message)
        update_profile({"name": name, "onboarding_step": "language_preference"})
        state["reply"] = (
            f"Hi {name}! 😊\n\n"
            "Which language do you prefer?\n[English] [हिंदी] [తెలుగు] [தமிழ்] [ಕನ್ನಡ]"
        )
        state["onboarding_step"] = "language_preference"
        return state

    # STEP 2 – language
    if current_step == "language_preference":
        lang_map = {
            "hindi": "hi",
            "हिंदी": "hi",
            "telugu": "te",
            "తెలుగు": "te",
            "tamil": "ta",
            "தமிழ்": "ta",
            "kannada": "kn",
            "ಕನ್ನಡ": "kn",
        }
        lower_msg = message.lower()
        lang = "en"
        for key, code in lang_map.items():
            if key in lower_msg:
                lang = code
                break
        # After language, ask if the user wants to continue with profile collection
        update_profile({"language_preference": lang, "onboarding_step": "continue_confirm"})
        state["reply"] = (
            "Great! Do you want to continue providing your details so I can find the best schemes for you? (yes/no)"
        )
        state["onboarding_step"] = "continue_confirm"
        return state

    # Subsequent fields order
    fields_order = [
        "state",
        "occupation",
        "caste_category",
        "gender",
        "age",
        "income_bracket",
        "land_size",
        "email",
    ]
    questions = {
        "state": "Which state are you from?",
        "occupation": "What is your occupation? (student/farmer/daily wage/business/govt/other)",
        "caste_category": "Caste category? (SC/ST/OBC/General)",
        "gender": "Gender? (Male/Female/Other)",
        "age": "How old are you?",
        "income_bracket": "Annual family income in rupees?",
        "land_size": "How much land do you own (in acres)? (Optional - enter 0 if none)",
        "email": "What is your email address? (Optional - for sending reminders about scheme deadlines)",
    }
    # Handle form/chat choice
    if current_step == "form_chat_choice":
        if message.strip().lower() in ["fill form", "form", "yes", "📝 fill form"]:
            # Start collecting the first missing field (state)
            update_profile({"onboarding_step": "state"})
            state["reply"] = "Great! Which state are you from?"
            state["onboarding_step"] = "state"
        elif message.strip().lower() in ["chat", "chat instead", "no", "just chat", "💬 chat instead"]:
            # Switch to chat mode - mark onboarding as complete
            update_profile({"onboarding_step": "complete"})
            state["reply"] = "Sure! Feel free to ask me any questions about welfare schemes or general topics. I'm here to help!"
            state["onboarding_step"] = "complete"
        else:
            state["reply"] = "Please choose: 'Fill Form' or 'Chat Instead'"
        return state

    if current_step == "continue_confirm":
        # User answered yes/no to continue profile collection
        if message.strip().lower() in ["yes", "y", "yeah", "sure"]:
            # Start collecting the first missing field (state)
            update_profile({"onboarding_step": "state"})
            state["reply"] = "Great! Which state are you from?"
            state["onboarding_step"] = "state"
        else:
            # User does not want to continue – switch to FAQ mode
            state["intent"] = "faq"
            state["reply"] = "No problem! Feel free to ask me any question about welfare schemes."
        return state
    if current_step in fields_order:
        update_profile({current_step: message, "onboarding_step": fields_order[fields_order.index(current_step) + 1] if current_step != fields_order[-1] else "confirmation"})
        # Determine next missing field
        user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
        missing = [f for f in REQUIRED_FIELDS if not user_doc.get(f)]
        if not missing:
            # Profile complete – show confirmation summary
            summary = (
                f"Please confirm your details:\n"
                f"Name: {user_doc.get('name')}\n"
                f"Language: {user_doc.get('language_preference')}\n"
                f"State: {user_doc.get('state')}\n"
                f"Occupation: {user_doc.get('occupation')}\n"
                f"Category: {user_doc.get('caste_category')}\n"
                f"Gender: {user_doc.get('gender')}\n"
                f"Age: {user_doc.get('age')}\n"
                f"Income: {user_doc.get('income_bracket')}\n"
                f"Land Size: {user_doc.get('land_size', 'Not provided')} acres\n"
                f"Email: {user_doc.get('email', 'Not provided')}\n\n"
                f"Is this correct? (Yes/No)"
            )
            state["reply"] = summary
            state["onboarding_step"] = "confirmation"
            state["confirmation_step"] = "awaiting_confirmation"
            update_profile({"onboarding_step": "confirmation", "confirmation_step": "awaiting_confirmation"})
            return state
        next_field = missing[0]
        state["reply"] = questions.get(next_field, f"Please provide your {next_field}.")
        state["onboarding_step"] = next_field
        return state

    # Handle confirmation step
    if current_step == "confirmation":
        if state.get("confirmation_step") == "awaiting_confirmation":
            user_response = message.strip().lower()
            # More flexible yes/no detection
            if user_response in ["yes", "y", "yeah", "correct", "right", "yes continue", "continue"]:
                # User confirmed – directly call handle_scheme_query
                update_profile({"confirmation_step": None})
                return handle_scheme_query(state)
            elif user_response in ["no", "n", "edit", "change", "edit details"]:
                state["reply"] = "Which field would you like to edit? (name, state, occupation, category, gender, age, income, land_size, email)"
                state["confirmation_step"] = "selecting_field"
                state["editing_field"] = None
                return state
            else:
                state["reply"] = "Please respond with 'Yes' to continue or 'No' to edit your details."
                return state
        elif state.get("confirmation_step") == "selecting_field":
            # Map user input to field names
            field_map = {
                "name": "name",
                "state": "state",
                "occupation": "occupation",
                "category": "caste_category",
                "gender": "gender",
                "age": "age",
                "income": "income_bracket",
                "land_size": "land_size",
                "email": "email"
            }
            field_to_edit = field_map.get(message.lower().strip())
            if not field_to_edit:
                state["reply"] = "Please choose: name, state, occupation, category, gender, age, income, land_size, or email"
                return state
            state["editing_field"] = field_to_edit
            state["reply"] = f"What is your new {field_to_edit}?"
            state["confirmation_step"] = "editing_value"
            return state
        elif state.get("confirmation_step") == "editing_value":
            field_to_edit = state.get("editing_field")
            if field_to_edit:
                update_profile({field_to_edit: message})
                # Show summary again
                user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
                summary = (
                    f"Please confirm your updated details:\n"
                    f"Name: {user_doc.get('name')}\n"
                    f"Language: {user_doc.get('language_preference')}\n"
                    f"State: {user_doc.get('state')}\n"
                    f"Occupation: {user_doc.get('occupation')}\n"
                    f"Category: {user_doc.get('caste_category')}\n"
                    f"Gender: {user_doc.get('gender')}\n"
                    f"Age: {user_doc.get('age')}\n"
                    f"Income: {user_doc.get('income_bracket')}\n\n"
                    f"Is this correct?"
                )
                state["reply"] = summary
                state["confirmation_step"] = "awaiting_confirmation"
                state["editing_field"] = None
                return state

    # Fallback – should not reach here
    state["reply"] = "Could you provide more details?"
    return state

def handle_faq(state: Dict[str, Any]) -> Dict[str, Any]:
    """Answer generic questions via Groq without needing a profile."""
    user_doc = state.get("user_profile", {})
    current_step = user_doc.get("onboarding_step", "name")
    
    # If still in onboarding, don't handle as FAQ - redirect to onboarding
    if current_step in ["name", "language_preference", "continue_confirm", "form_chat_choice", "state", "occupation", "caste_category", "gender", "age", "income_bracket", "confirmation"]:
        state["intent"] = "onboarding"
        return handle_onboarding(state)
    
    language = user_doc.get("language_preference", "en")
    
    # Import language prompts
    from agent.languages import SYSTEM_PROMPTS
    system_prompt = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["en"])
    reply = safe_groq_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["message"]},
        ],
        temperature=0.7,
    )
    state["reply"] = reply or "I'm here to help! Ask me about welfare schemes."
    
    # Calculate confidence score
    state["confidence"] = calculate_confidence(state["message"], "faq", user_doc)
    
    return state

def handle_scheme_query(state: Dict[str, Any]) -> Dict[str, Any]:
    """Return matching schemes based on the stored user profile."""
    session_id = state["session_id"]
    user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
    
    # Helper to persist step
    def update_profile(updates: Dict[str, Any]):
        sync_users_collection.update_one(
            {"session_id": session_id},
            {"$set": updates},
            upsert=True,
        )
    
    try:
        from agent.eligibility import match_schemes
        schemes = match_schemes(user_doc, sync_schemes_collection)
        logger.info(f"DEBUG handle_scheme_query: Found {len(schemes)} schemes")
        if schemes:
            # Generate chips for scheme selection
            scheme_chips = [s['name'] for s in schemes[:10]]
            state["chips"] = scheme_chips
            state["schemes"] = schemes
            state["reply"] = f"I found {len(schemes)} schemes that match your profile! Select a scheme to learn more:"
        else:
            state["reply"] = "No exact matches found right now. Check back later for new schemes!"
            state["schemes"] = []
            state["chips"] = []
    except Exception as e:
        logger.error(f"Scheme query error: {e}")
        state["reply"] = "I'm having trouble fetching schemes right now. Please try again later."
        state["schemes"] = []
        state["chips"] = []
    
    # Mark onboarding as complete after scheme query
    update_profile({"onboarding_step": "complete"})
    state["onboarding_step"] = "complete"
    state["intent"] = "scheme_query"  # Ensure intent is set for chip generation
    
    # Calculate confidence score
    state["confidence"] = calculate_confidence(state.get("message", ""), "scheme_query", user_doc)
    
    return state