# app/__init__.py
from dotenv import load_dotenv
load_dotenv(".secrets")
from flask import Flask
from .config import Config
from .extensions import db, migrate
from .routes.main import main_bp
from dotenv import load_dotenv
import os

# Load environment variables from .secrets or .env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".secrets"))
load_dotenv()  # fallback .env if present

def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(main_bp)

    return app
