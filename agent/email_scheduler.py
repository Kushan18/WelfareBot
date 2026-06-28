"""Email reminder scheduler for WelfareBot using APScheduler."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from typing import Dict, List, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Email configuration
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
FROM_EMAIL = os.getenv('FROM_EMAIL', SMTP_USER)

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
client = MongoClient(MONGODB_URI)
db = client['welfarebot']
users_collection = db['users']
schemes_collection = db['schemes']

# Initialize scheduler
scheduler = AsyncIOScheduler()


def send_email(to_email: str, subject: str, body: str, html: bool = False) -> bool:
    """Send an email using SMTP."""
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        if html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def get_upcoming_deadlines(days: int = 7) -> List[Dict[str, Any]]:
    """Get schemes with deadlines within the specified days."""
    cutoff_date = datetime.utcnow() + timedelta(days=days)
    schemes = list(schemes_collection.find({
        'deadline': {'$lte': cutoff_date, '$gte': datetime.utcnow()}
    }))
    return schemes


def get_users_for_scheme(scheme_id: str) -> List[Dict[str, Any]]:
    """Get users who might be eligible for a specific scheme."""
    # Simple implementation - get all users with email
    users = list(users_collection.find({'email': {'$exists': True, '$ne': None}}))
    return users


def schedule_deadline_reminders():
    """Schedule email reminders for upcoming scheme deadlines."""
    schemes = get_upcoming_deadlines(days=7)
    
    for scheme in schemes:
        scheme_id = str(scheme['_id'])
        deadline = scheme.get('deadline')
        scheme_name = scheme.get('name', 'Unknown Scheme')
        
        if not deadline:
            continue
        
        # Schedule reminders at 7 days, 3 days, and 1 day before deadline
        reminder_days = [7, 3, 1]
        
        for days_before in reminder_days:
            reminder_date = deadline - timedelta(days=days_before)
            
            if reminder_date > datetime.utcnow():
                job_id = f"reminder_{scheme_id}_{days_before}d"
                
                # Check if job already exists
                if scheduler.get_job(job_id):
                    continue
                
                scheduler.add_job(
                    send_scheme_reminder,
                    trigger=DateTrigger(run_date=reminder_date),
                    args=[scheme_id, days_before],
                    id=job_id,
                    replace_existing=True
                )
                logger.info(f"Scheduled reminder for {scheme_name} at {days_before} days before deadline")


def send_scheme_reminder(scheme_id: str, days_before: int):
    """Send reminder email for a specific scheme."""
    from agent.email_templates import get_reminder_template
    
    scheme = schemes_collection.find_one({'_id': scheme_id})
    if not scheme:
        return
    
    users = get_users_for_scheme(scheme_id)
    scheme_name = scheme.get('name', 'Unknown Scheme')
    deadline = scheme.get('deadline')
    
    subject, body, html_body = get_reminder_template(scheme_name, deadline, days_before)
    
    for user in users:
        email = user.get('email')
        if email and user.get('email_reminders', True):
            send_email(email, subject, body, html=True)


def start_scheduler():
    """Start the APScheduler."""
    scheduler.start()
    schedule_deadline_reminders()
    logger.info("Email scheduler started")


def shutdown_scheduler():
    """Shutdown the scheduler."""
    scheduler.shutdown()
    logger.info("Email scheduler shutdown")


# Manual trigger for testing
def send_test_email(to_email: str):
    """Send a test email."""
    subject = "WelfareBot Test Email"
    body = """
    <html>
    <body>
        <h2>Test Email from WelfareBot</h2>
        <p>This is a test email to verify email configuration.</p>
        <p>If you received this, email reminders are working correctly!</p>
    </body>
    </html>
    """
    return send_email(to_email, subject, body, html=True)
