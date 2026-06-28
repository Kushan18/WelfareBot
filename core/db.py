import os
import logging
from typing import Optional, Dict, List
from pymongo import MongoClient
import motor.motor_asyncio
from dotenv import load_dotenv

# Simple in‑memory collection fallback
# Simple in‑memory collection fallback (synchronous)
class InMemoryCollection:
    def __init__(self):
        self.store: Dict[str, Dict] = {}

    def find_one(self, filter: Dict) -> Optional[Dict]:
        # Assumes filter contains a single key like "session_id"
        key, value = next(iter(filter.items()))
        return self.store.get(value)

    def update_one(self, filter: Dict, update: Dict, upsert: bool = False):
        key, value = next(iter(filter.items()))
        if value not in self.store:
            if upsert:
                self.store[value] = {}
            else:
                return
        # Apply $set updates
        set_doc = update.get("$set", {})
        self.store[value].update(set_doc)

    def insert_one(self, document: Dict) -> None:
        self.store[document.get("_id", str(len(self.store) + 1))] = document

# Simple in‑memory collection fallback (asynchronous placeholder)
class InMemoryAsyncCollection:
    def __init__(self):
        self.store: Dict[str, Dict] = {}

    async def insert_one(self, document: Dict) -> None:
        self.store[document.get("_id", str(len(self.store) + 1))] = document

load_dotenv()

logger = logging.getLogger(__name__)

# Load MongoDB URI – if not set, we keep collections as in‑memory fallback.
MONGODB_URI: Optional[str] = os.getenv("MONGODB_URI")

if MONGODB_URI:
    try:
        # Synchronous client for quick reads/writes
        sync_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=2000)
        # Verify connection
        sync_client.admin.command("ping")
        sync_db = sync_client["welfarebot"]
        users_collection = sync_db["users"]
        schemes_collection = sync_db["schemes"]
    except Exception as e:
        logger.warning(f"MongoDB sync client could not connect: {e}")
        users_collection = InMemoryCollection()
        schemes_collection = InMemoryCollection()
else:
    logger.warning("MONGODB_URI not set – using in‑memory collections.")
    users_collection = InMemoryCollection()
    schemes_collection = InMemoryCollection()

# Asynchronous client – also safe‑fails.
if MONGODB_URI:
    try:
        async_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=2000)
        async_db = async_client["welfarebot"]
        conversations_collection = async_db["conversations"]
    except Exception as e:
        logger.warning(f"MongoDB async client could not connect: {e}")
        conversations_collection = InMemoryAsyncCollection()
else:
    conversations_collection = InMemoryAsyncCollection()

# Exported symbols for other modules.
__all__ = ["users_collection", "schemes_collection", "conversations_collection"]
