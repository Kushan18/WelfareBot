import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve project root (two levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Load environment variables
load_dotenv(dotenv_path=ENV_PATH)

class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    MONGODB_URI: str = os.getenv("MONGODB_URI")

    def __post_init__(self):
        if not self.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY not set in .env")
        if not self.MONGODB_URI:
            raise RuntimeError("MONGODB_URI not set in .env")

settings = Settings()
