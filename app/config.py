import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # /app -> project root

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-me")

    # ALWAYS APP ROOT, NEVER INSTANCE FOLDER
    DB_PATH = BASE_DIR / "runbook.db"

    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # future use
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
