"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / os.getenv("STATIC_DIR", "static")
REPORTS_DIR = STATIC_DIR / "reports"
DIAGRAMS_DIR = STATIC_DIR / "diagrams"
DATA_DIR = BASE_DIR / "data"

# Ensure directories exist
for d in (REPORTS_DIR, DIAGRAMS_DIR, DATA_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Report server
REPORT_BASE_URL = os.getenv("REPORT_BASE_URL", "http://localhost:8080").rstrip("/")
REPORT_SERVER_PORT = int(os.getenv("REPORT_SERVER_PORT", "8080"))

# Database
DATABASE_PATH = DATA_DIR / "jobs.db"
