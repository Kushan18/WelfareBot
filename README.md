# WelfareBot Backend

FastAPI backend for the WelfareBot application with MongoDB database, LangGraph orchestration, and automated scheme scraping.

## Setup

1. Create virtual environment:
```bash
python -m venv venv
```

2. Activate virtual environment:
- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (CMD): `.venv\Scripts\activate.bat`
- macOS/Linux: `source venv/bin/activate`

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers (for myscheme scraping):
```bash
playwright install chromium
```

5. Set up environment variables:
```bash
copy .env.example .env
# Edit .env with your actual keys:
# GROQ_API_KEY=YOUR_GROQ_KEY
# MONGODB_URI=YOUR_MONGODB_CONNECTION_STRING
# ADMIN_API_KEY=admin-secret-key-123
```

6. Run development server:
```bash
uvicorn main:app --reload
```

The API will be available at http://127.0.0.1:8000.

## API Endpoints

### Core Endpoints
- `GET /health` - Health check
- `POST /chat` - Chat endpoint with session management
- `GET /schemes` - Get all schemes

### Voice Input
- `POST /voice-input` - Upload audio for transcription (requires STT integration)

### Email Reminders
- `POST /send-reminder` - Send immediate reminder
- `POST /schedule-reminder` - Schedule reminder for specific date
- `GET /reminders/{session_id}` - Get user's reminders

### Admin Dashboard (Requires API Key)
All admin endpoints require `X-Admin-API-Key` header with the value from `ADMIN_API_KEY` environment variable.

- `GET /admin/users` - Get all users
- `GET /admin/conversations` - Get all conversations
- `GET /admin/analytics` - Get analytics data
- `DELETE /admin/users/{session_id}` - Delete user
- `PUT /admin/schemes` - Add new scheme
- `DELETE /admin/schemes/{scheme_id}` - Delete scheme

Example admin request:
```bash
curl -X GET "http://127.0.0.1:8000/admin/users" -H "X-Admin-API-Key: admin-secret-key-123"
```

## Features

- **Onboarding Flow**: Name extraction, language preference, profile collection (including email), confirmation
- **Scheme Matching**: Eligibility-based scheme recommendations
- **Confidence Scoring**: Query confidence evaluation
- **Session Persistence**: MongoDB-based session management
- **Conversation History**: Full chat history storage
- **Automated Scraping**: APScheduler runs scraper every 3 days
- **Multi-language Support**: English, Hindi, Telugu, Tamil, Kannada
- **Admin Authentication**: API key-based authentication for admin endpoints

## Scraping

The scraper runs automatically every 3 days via APScheduler. To manually trigger scraping:
```bash
python -m scraper.seed
```

To force refresh (clear staging first):
```bash
python -m scraper.seed --force
```

## Database Collections

- `users` - User profiles and session data (includes email)
- `schemes` - Live welfare schemes
- `staging` - Staged schemes pending approval
- `conversations` - Chat history
- `reminders` - Scheduled reminders
