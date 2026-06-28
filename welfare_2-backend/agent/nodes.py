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

# Keywords that indicate user wants to find schemes for themselves (needs profile)
PROFILE_REQUIRED_KEYWORDS = [
    "eligible for",
    "am i eligible",
    "my schemes",
    "schemes for me",
    "what schemes",
    "find schemes",
    "match me",
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
    # fallback – first word (but exclude common words and phrases)
    words = text.strip().split()
    if words:
        first_word = words[0].capitalize()
        # Skip if it's a common filler word or greeting
        skip_words = ["i", "hi", "hello", "hey", "the", "a", "an", "my", "am", "is", "welcome", "to", "welfarebot", "we", "help"]
        if first_word.lower() not in skip_words:
            return first_word
    return "Friend"

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

# ---------- Intent Detection & Handlers ----------
def detect_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Determine user intent for routing with smart detection.
    Updates `state["intent"].
    """
    message = state.get("message", "").lower()
    session_id = state.get("session_id")
    user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
    
    # Check if user is in middle of onboarding
    onboarding_step = user_doc.get("onboarding_step", "name")
    
    # Active onboarding steps - if user is in any of these, always route to onboarding
    active_onboarding_steps = [
        "language_preference", "form_chat_choice", "state", "occupation", 
        "caste_category", "gender", "age", "income_bracket", "confirmation"
    ]
    
    is_in_active_onboarding = onboarding_step in active_onboarding_steps
    
    # Scheme‑related keywords
    is_scheme_question = any(kw in message for kw in SCHEME_KEYWORDS)
    # Check if user wants personal scheme matching (needs profile)
    needs_profile = any(kw in message for kw in PROFILE_REQUIRED_KEYWORDS)
    profile_complete = all(user_doc.get(f) for f in REQUIRED_FIELDS)
    
    # Check if message looks like a name (simple heuristic: single word, not a keyword)
    words = message.strip().split()
    looks_like_name = len(words) <= 2 and not any(kw in message for kw in SCHEME_KEYWORDS + ["what", "how", "why", "tell", "know", "want", "need"])
    
    # Smart routing logic:
    # 1. If user is in active onboarding step, always continue onboarding
    if is_in_active_onboarding:
        intent = "onboarding"
    # 2. If user has name but not complete, continue onboarding
    elif onboarding_step != "complete" and user_doc.get("name"):
        intent = "onboarding"
    # 3. If user provides a name (looks like name and no name yet) -> onboarding
    elif looks_like_name and not user_doc.get("name"):
        intent = "onboarding"
    # 4. If user wants personal scheme matching but doesn't have complete profile -> onboarding
    elif needs_profile and not profile_complete:
        intent = "onboarding"
    # 5. If user wants personal scheme matching and has complete profile -> scheme_query
    elif needs_profile and profile_complete:
        intent = "scheme_query"
    # 6. If user asks general scheme questions (not personal) -> FAQ with general knowledge
    elif is_scheme_question:
        intent = "faq"
    # 7. Otherwise (general questions, greetings, etc.) -> FAQ with general knowledge
    else:
        intent = "faq"
    
    state["intent"] = intent
    state["user_profile"] = user_doc
    logger.info(f"detect_intent -> {intent} (onboarding_step: {onboarding_step})")
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
        # After language, ask if user wants to fill form or chat
        update_profile({"language_preference": lang, "onboarding_step": "form_chat_choice"})
        state["reply"] = (
            "Would you like to fill a form or just chat?"
        )
        state["onboarding_step"] = "form_chat_choice"
        return state

    # Subsequent fields order
    fields_order = [
        "state",
        "occupation",
        "caste_category",
        "gender",
        "age",
        "income_bracket",
    ]
    questions = {
        "state": "Which state are you from?",
        "occupation": "What is your occupation? (student/farmer/daily wage/business/govt/other)",
        "caste_category": "Caste category? (SC/ST/OBC/General)",
        "gender": "Gender? (Male/Female/Other)",
        "age": "How old are you?",
        "income_bracket": "Annual family income in rupees?",
    }
    
    # Handle form/chat choice
    if current_step == "form_chat_choice":
        if message.strip().lower() in ["fill form", "form", "yes"]:
            # Start collecting profile fields
            update_profile({"onboarding_step": "state"})
            state["reply"] = "Great! Which state are you from?"
            state["onboarding_step"] = "state"
        elif message.strip().lower() in ["chat", "chat instead", "no", "just chat"]:
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
                f"Please confirm your details:\n\n"
                f"Name: {user_doc.get('name')}\n"
                f"Language: {user_doc.get('language_preference')}\n"
                f"State: {user_doc.get('state')}\n"
                f"Occupation: {user_doc.get('occupation')}\n"
                f"Category: {user_doc.get('caste_category')}\n"
                f"Gender: {user_doc.get('gender')}\n"
                f"Age: {user_doc.get('age')}\n"
                f"Income: {user_doc.get('income_bracket')}\n"
                f"Land Holding: {user_doc.get('land_holding', 'Not specified')}\n\n"
                f"Is this correct?"
            )
            state["reply"] = summary
            state["onboarding_step"] = "confirmation"
            update_profile({"confirmation_step": "awaiting_confirmation"})
            state["confirmation_step"] = "awaiting_confirmation"
            return state
        next_field = missing[0]
        state["reply"] = questions.get(next_field, f"Please provide your {next_field}.")
        state["onboarding_step"] = next_field
        return state

    # Handle confirmation step
    if current_step == "confirmation":
        # Get confirmation_step from user profile (stored in MongoDB)
        confirmation_step = user_doc.get("confirmation_step", "awaiting_confirmation")
        
        if confirmation_step == "awaiting_confirmation":
            if message.strip().lower() in ["yes", "y", "yeah", "correct", "right"]:
                # User confirmed – mark profile as complete and proceed to scheme matching
                update_profile({"onboarding_step": "complete", "confirmation_step": "completed"})
                state["intent"] = "scheme_query"
                return handle_scheme_query(state)
            elif message.strip().lower() in ["no", "n", "edit", "change"]:
                update_profile({"confirmation_step": "selecting_field"})
                state["reply"] = "Which field would you like to edit? (name, state, occupation, category, gender, age, income)"
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
                "income": "income_bracket"
            }
            field_to_edit = field_map.get(message.lower().strip())
            if not field_to_edit:
                state["reply"] = "Please choose: name, state, occupation, category, gender, age, or income"
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
    state["reply"] = reply or "I’m here to help! Ask me about welfare schemes."
    return state

def handle_scheme_query(state: Dict[str, Any]) -> Dict[str, Any]:
    """Return matching schemes based on the stored user profile with Phase 8 3-tier retrieval."""
    session_id = state["session_id"]
    user_message = state["message"].lower()
    user_doc = sync_users_collection.find_one({"session_id": session_id}) or {}
    
    # Check if user is asking detailed question about a specific scheme
    scheme_keywords = ["what", "how", "documents", "need", "require", "details", "benefits", "eligible"]
    asking_details = any(kw in user_message for kw in scheme_keywords)
    
    try:
        from agent.eligibility import match_schemes
        schemes = match_schemes(user_doc, sync_schemes_collection)
        
        if not schemes:
            state["reply"] = "No matching schemes found."
            return state
        
        # If asking for details, use Phase 8 3-tier retrieval
        if asking_details and schemes:
            top_scheme = schemes[0]
            scheme_name = top_scheme.get('name', '')
            
            logger.info(f"User asking details about: {scheme_name}")
            
            # TIER 1: Try ChromaDB first
            try:
                from agent.chroma_retrieval import get_scheme_details_from_chroma
                chroma_result = get_scheme_details_from_chroma(scheme_name)
                
                if chroma_result and chroma_result.get("found"):
                    logger.info(f"Found scheme in ChromaDB: {scheme_name}")
                    # Use Groq to answer based on ChromaDB data
                    answer = safe_groq_chat([
                        {"role": "system", "content": f"You are a helpful assistant for Indian welfare schemes. Answer the user's question based ONLY on the following scheme data. If the answer is not in the data, say so.\n\nScheme Data:\n{chroma_result['text']}"},
                        {"role": "user", "content": state["message"]}
                    ])
                    state["reply"] = f"For **{scheme_name}**:\n\n{answer}"
                    return state
            except Exception as e:
                logger.warning(f"ChromaDB retrieval failed: {e}")
            
            # TIER 2: Try live fetch
            try:
                import asyncio
                from live_fetcher.live_scheme_fetcher import fetch_scheme_details_live
                from live_fetcher.groq_live_parser import answer_scheme_question_with_live_data
                
                logger.info(f"ChromaDB miss, trying live fetch for: {scheme_name}")
                live_data = asyncio.run(fetch_scheme_details_live(scheme_name))
                
                if live_data:
                    # Get Groq answer based on live data
                    answer = answer_scheme_question_with_live_data(
                        groq_client, 
                        scheme_name, 
                        state["message"], 
                        live_data
                    )
                    
                    state["reply"] = f"For **{scheme_name}**:\n\n{answer}"
                    
                    # Store in ChromaDB for future use
                    try:
                        from agent.chroma_retrieval import populate_chroma_from_mongodb
                        populate_chroma_from_mongodb(sync_schemes_collection)
                    except Exception as chroma_error:
                        logger.warning(f"Failed to update ChromaDB: {chroma_error}")
                    
                    return state
            except Exception as e:
                logger.warning(f"Live fetch failed: {e}")
            
            # TIER 3: Fallback to Groq knowledge with disclaimer
            logger.info(f"Live fetch failed, using Groq knowledge for: {scheme_name}")
            answer = safe_groq_chat([
                {"role": "system", "content": f"You are a helpful assistant for Indian welfare schemes. The user is asking about '{scheme_name}'. Provide helpful information based on your knowledge, but clearly state that this information may be outdated and they should verify from the official government website. Do not hallucinate specific details like income limits or deadlines."},
                {"role": "user", "content": state["message"]}
            ])
            state["reply"] = f"For **{scheme_name}**:\n\n{answer}\n\n*Note: This information is based on general knowledge and may be outdated. Please verify from the official government website.*"
        
        else:
            # Just show matching schemes list and set schemes for chips
            scheme_list = "\n".join([
                f"• **{s['name']}** - {s['description']}\n  Apply: {s['apply_link']}"
                for s in schemes[:3]
            ])
            
            state["reply"] = f"Found {len(schemes)} matching schemes:\n\n{scheme_list}\n\nSelect a scheme to learn more or apply!"
            state["schemes"] = schemes  # Pass schemes to chip generator
    
    except Exception as e:
        logger.error(f"Scheme query error: {e}")
        state["reply"] = "I had trouble retrieving schemes. Please try again."
    
    return state

def calculate_confidence(message: str, user_doc: dict) -> float:
    """Calculate confidence score for the response (0-100)."""
    confidence = 85.0  # Base confidence
    
    # Higher confidence for scheme-related questions
    scheme_keywords = ["scheme", "yojana", "benefit", "eligible", "pension", "scholarship", "kisan", "farmer", "student"]
    if any(kw in message.lower() for kw in scheme_keywords):
        confidence += 10
    
    # Lower confidence for very general or vague questions
    vague_keywords = ["something", "anything", "help", "what", "how"]
    if len(message.split()) < 3 or any(kw in message.lower() for kw in vague_keywords):
        confidence -= 15
    
    # Higher confidence if user has profile
    if user_doc and user_doc.get("name"):
        confidence += 5
    
    # Clamp between 0 and 100
    return max(0, min(100, confidence))
