# WelfareBot

WelfareBot is an AI-powered welfare assistant for Indian citizens. It helps users discover government welfare schemes they are eligible for.

## Tech Stack

- **Frontend**: React
- **Backend**: FastAPI
- **Database**: MongoDB Atlas
- **LLM**: Groq
- **Orchestration**: LangGraph
- **Vector Storage**: ChromaDB
- **Background Tasks**: APScheduler
- **Scraping**: Various government sources

## Setup Instructions

### Backend Setup

1. Navigate to the project directory:
   ```bash
   cd WELFARE_BOTT2
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - **Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (Command Prompt):**
     ```cmd
     .\venv\Scripts\activate.bat
     ```
   - **macOS / Linux:**
     ```bash
     source venv/bin/activate
     ```

4. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Set up the environment variables:
   ```bash
   copy .env.example .env
   # Then edit .env to add your actual keys:
   # GROQ_API_KEY=YOUR_GROQ_KEY
   # MONGODB_URI=YOUR_MONGODB_CONNECTION_STRING
   ```

6. Run the development server:
   ```bash
   uvicorn main:app --reload
   ```

By default, the API will be available at http://127.0.0.1:8000.

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install the dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

The frontend will be available at http://localhost:3000.

## API Endpoints

### 1. Health Check
- **Endpoint:** `GET /health`
- **Response:**
  ```json
  {
    "status": "running",
    "db": "connected"
  }
  ```

### 2. Chat Endpoint
- **Endpoint:** `POST /chat`
- **Request Body:**
  ```json
  {
    "session_id": "optional-session-id",
    "message": "Hello"
  }
  ```
- **Response:**
  ```json
  {
    "reply": "Hello! How can I help you?",
    "show_form_choice": false,
    "clear_session": false,
    "chips": ["Start Over", "Find My Schemes"]
  }
  ```

### 3. Submit Profile
- **Endpoint:** `POST /submit-profile`
- **Request Body:**
  ```json
  {
    "session_id": "session-id",
    "name": "John Doe",
    "language_preference": "English",
    "state": "Telangana",
    "occupation": "Farmer",
    "caste_category": "General",
    "gender": "Male",
    "age": "30",
    "income_bracket": "Below 1 Lakh"
  }
  ```

## API Documentation
Once the server is running, you can access the interactive API docs at:
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
