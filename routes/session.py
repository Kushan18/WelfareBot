from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional

from core.db import users_collection

router = APIRouter()

_fallback_store: Dict[str, Dict[str, Any]] = {}

def _get_collection() -> Optional[Any]:
    return users_collection

def _default_session(session_id: str) -> Dict[str, Any]:
    return {"session_id": session_id, "step": "name", "data": {}}

@router.get("/session")
def get_session(session_id: str = Query(..., description="Unique session identifier")):
    collection = _get_collection()
    if collection is None:
        session = _fallback_store.get(session_id)
        if not session:
            session = _default_session(session_id)
            _fallback_store[session_id] = session
        return session
    doc = collection.find_one({"session_id": session_id})
    if not doc:
        new_doc = _default_session(session_id)
        collection.insert_one(new_doc)
        return new_doc
    return {"session_id": doc.get("session_id", session_id), "step": doc.get("step", "name"), "data": doc.get("data", {})}

class ProfilePayload(BaseModel):
    session_id: str
    name: str
    language: str
    state: str
    occupation: str
    category: str
    gender: str
    age: int
    income: str

@router.post("/submit-profile")
def submit_profile(payload: ProfilePayload):
    collection = _get_collection()
    session_data = {"session_id": payload.session_id, "step": "chat", "data": payload.dict()}
    if collection is None:
        _fallback_store[payload.session_id] = session_data
        return session_data
    update_doc = {"$set": {"name": payload.name, "language": payload.language, "state": payload.state, "occupation": payload.occupation, "category": payload.category, "gender": payload.gender, "age": payload.age, "income": payload.income, "step": "chat", "data": payload.dict()}}
    collection.update_one({"session_id": payload.session_id}, update_doc, upsert=True)
    return session_data
