import asyncio
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo import MongoClient
from groq import Groq
import os
import logging

from scraper.scheme_scraper import fetch_schemes_from_myscheme
from scraper.groq_structurer import structure_scheme_with_groq

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def run_weekly_scraper():
    """
    Weekly scraper job - fetch, structure, save to MongoDB staging
    """
    logger.info("[SCRAPER] Starting weekly scheme fetch...")
    
    try:
        # Initialize clients
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        mongo_client = MongoClient(os.getenv("MONGODB_URI"))
        db = mongo_client["welfarebot"]
        staging = db["staging"]
        
        # Fetch schemes
        raw_schemes = asyncio.run(fetch_schemes_from_myscheme())
        logger.info(f"[SCRAPER] Fetched {len(raw_schemes)} raw schemes")
        
        # Structure each with Groq
        structured_schemes = []
        for raw in raw_schemes:
            structured = structure_scheme_with_groq(groq_client, raw)
            if structured:
                structured["scraped_at"] = datetime.utcnow()
                structured["status"] = "pending_approval"  # Admin must approve
                structured_schemes.append(structured)
        
        # Save to staging collection
        if structured_schemes:
            staging.delete_many({})  # Clear old staging
            staging.insert_many(structured_schemes)
            logger.info(f"[SCRAPER] Saved {len(structured_schemes)} schemes to staging")
        
        logger.info("[SCRAPER] Weekly scraper completed successfully")
        
    except Exception as e:
        logger.error(f"[SCRAPER] FATAL ERROR: {e}", exc_info=True)

def start_scheduler():
    """Start APScheduler for 3-day interval runs"""
    
    # Run every 3 days
    scheduler.add_job(
        run_weekly_scraper,
        'interval',
        days=3,
        id='scheme_scraper'
    )
    
    if not scheduler.running:
        scheduler.start()
        logger.info("[SCRAPER] 3-day scheduler started")
