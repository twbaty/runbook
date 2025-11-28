# app/config.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-me")

     # ALWAYS use the project root DB
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'runbook.db'}"
    )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Allow ServiceNow CSV uploads up to 100MB
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024

    # for later: API keys, etc.
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
