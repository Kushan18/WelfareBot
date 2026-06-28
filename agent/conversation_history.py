"""Conversation history management for WelfareBot."""
from typing import Dict, List, Any, Optional
from datetime import datetime
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
client = MongoClient(MONGODB_URI)
db = client['welfarebot']
history_collection = db['conversation_history']


def save_conversation(session_id: str, messages: List[Dict[str, Any]], user_profile: Dict[str, Any]) -> str:
    """Save a conversation to history."""
    conversation = {
        'session_id': session_id,
        'messages': messages,
        'user_profile': user_profile,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'message_count': len(messages)
    }
    
    # Check if conversation exists
    existing = history_collection.find_one({'session_id': session_id})
    if existing:
        history_collection.update_one(
            {'session_id': session_id},
            {
                '$set': {
                    'messages': messages,
                    'updated_at': datetime.utcnow(),
                    'message_count': len(messages)
                }
            }
        )
        return str(existing['_id'])
    else:
        result = history_collection.insert_one(conversation)
        return str(result.inserted_id)


def get_conversation_history(session_id: str) -> Optional[Dict[str, Any]]:
    """Get conversation history for a session."""
    return history_collection.find_one({'session_id': session_id})


def get_all_conversations(limit: int = 50) -> List[Dict[str, Any]]:
    """Get all conversations, sorted by most recent."""
    return list(history_collection.find().sort('updated_at', -1).limit(limit))


def search_conversations(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search conversations by message content."""
    return list(history_collection.find(
        {'messages.text': {'$regex': query, '$options': 'i'}}
    ).sort('updated_at', -1).limit(limit))


def delete_conversation(session_id: str) -> bool:
    """Delete a conversation from history."""
    result = history_collection.delete_one({'session_id': session_id})
    return result.deleted_count > 0


def get_conversation_stats() -> Dict[str, Any]:
    """Get statistics about conversations."""
    total = history_collection.count_documents({})
    total_messages = history_collection.aggregate([
        {'$group': {'_id': None, 'total': {'$sum': '$message_count'}}}
    ])
    total_messages = list(total_messages)[0]['total'] if total_messages else 0
    
    return {
        'total_conversations': total,
        'total_messages': total_messages
    }
