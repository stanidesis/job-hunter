import os
from dotenv import load_dotenv

load_dotenv()

# Database (override with DB_PATH for Docker volume mounts, e.g. /data/jobs.db)
_DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jobs.db")
DB_PATH = os.getenv("DB_PATH", _DEFAULT_DB)

# API Keys (optional for test version)
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

# Email Settings (Resend API)
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "")
RESEND_TO = os.getenv("RESEND_TO", "")

# Daily digest scheduler defaults (overridden by active profile outreach settings)
DAILY_EMAIL_HOUR = int(os.getenv("DAILY_EMAIL_HOUR", "9"))
DAILY_EMAIL_MINUTE = int(os.getenv("DAILY_EMAIL_MINUTE", "0"))
DAILY_EMAIL_TIMEZONE = os.getenv("DAILY_EMAIL_TIMEZONE", "UTC")
DAILY_JOBS_COUNT = int(os.getenv("DAILY_JOBS_COUNT", "15"))

# Google Sheets
GOOGLE_SHEETS_CREDS = os.getenv("GOOGLE_SHEETS_CREDS", "credentials.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

# Minimum relevance score to show in polished results (profile can override)
MIN_RELEVANCE_SCORE = 50

# Server (local dev only; Docker/CMD sets bind address separately)
PORT = int(os.getenv("PORT", "8000"))
