"""
Core configuration settings for StarApp full-stack backend.
"""
import os
from pathlib import Path

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables from .env if present
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# Configuration values
HOST: str = os.getenv("HOST", "127.0.0.1")
PORT: int = int(os.getenv("PORT", "8000"))
DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
SECRET_KEY: str = os.getenv("SECRET_KEY", "starapp_super_secret_local_dev_key_2026_change_in_production")
SESSION_COOKIE_NAME: str = "starapp_session"
SESSION_EXPIRE_HOURS: int = int(os.getenv("SESSION_EXPIRE_HOURS", "24"))

# Authoritative SQLite database path
DATABASE_PATH: Path = BASE_DIR / os.getenv("DATABASE_URL", "data/starapp.db")
os.environ["STARAPP_DB_PATH"] = str(DATABASE_PATH)

# External Integrations
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
