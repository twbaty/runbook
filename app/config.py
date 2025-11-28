# app/config.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-me")

    # Absolute path to DB in project root (NOT instance/)
    DB_PATH = BASE_DIR / "runbook.db"

    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH.as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
