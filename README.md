# WelfareBot

Full-stack WelfareBot application with React frontend and FastAPI backend.

## Project Structure

```
welfare_2-backend/
├── frontend/          # React frontend
├── agent/            # LangGraph agent logic
├── scraper/          # Scheme scraping modules
├── rag/              # RAG retrieval modules
├── main.py           # FastAPI backend
└── requirements.txt  # Python dependencies
```

## Quick Start

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\Activate  # Windows
# or: source venv/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers
playwright install chromium

# 4. Set up environment variables
copy .env.example .env
# Edit .env with your actual keys

# 5. Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

## Setup Instructions

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

## Deployment on Render

### Backend Deployment

1. Create a new Web Service on Render
2. Connect your GitHub repository (WelfareBot)
3. Set environment variables:
   - `GROQ_API_KEY`: Your Groq API key
   - `MONGODB_URI`: Your MongoDB connection string
   - `ADMIN_API_KEY`: Your admin API key
4. Build command:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
5. Start command:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
6. Click "Deploy Web Service"

### Frontend Deployment

1. Create a new Web Service on Render
2. Connect your GitHub repository (WelfareBot - frontend branch or separate repo)
3. Set environment variable:
   - `REACT_APP_API_URL`: Your backend Render URL (e.g., https://your-backend.onrender.com)
4. Build command:
   ```bash
   npm install
   npm run build
   ```
5. Start command:
   ```bash
   npm start
   ```
6. Click "Deploy Web Service"
