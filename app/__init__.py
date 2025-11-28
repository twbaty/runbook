# app/__init__.py
import os
from flask import Flask
from dotenv import load_dotenv

from .config import Config
from .extensions import db, migrate
from .routes.main import main_bp
from .services.ollama_manager import ensure_ollama_ready


def load_environment():
    """
    Load secrets and environment variables from .secrets and .env.
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))

    secrets_file = os.path.join(base_dir, ".secrets")
    env_file = os.path.join(base_dir, ".env")

    if os.path.exists(secrets_file):
        load_dotenv(secrets_file)

    if os.path.exists(env_file):
        load_dotenv(env_file)


# Load environment variables immediately on module import
load_environment()


def create_app(config_class: type[Config] = Config) -> Flask:
    """
    Application factory.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Ensure Ollama + model availability BEFORE registering blueprints
    ensure_ollama_ready()

    # Register blueprints
    app.register_blueprint(main_bp)

    return app
