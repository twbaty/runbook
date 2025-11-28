# app/__init__.py
import os
from flask import Flask
from dotenv import load_dotenv

from .config import Config
from .extensions import db, migrate
from .routes.main import main_bp


def create_app(config_class: type[Config] = Config) -> Flask:
    # Load secrets BEFORE creating the app
    secrets_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".secrets")
    load_dotenv(secrets_file)
    load_dotenv()  # fallback for .env

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inject the OPENAI_API_KEY into the Flask config
    app.config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

    # Debug: show we actually loaded it
    print("DEBUG: Flask OPENAI_API_KEY =", app.config.get("OPENAI_API_KEY"))

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(main_bp)

    return app
