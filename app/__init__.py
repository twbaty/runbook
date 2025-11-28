# app/__init__.py
from flask import Flask
from .extensions import db
from .config import Config
import os

def create_app():
    # DO NOT use instance_relative_config=True
    app = Flask(__name__, template_folder="templates")

    # Load your config normally
    app.config.from_object(Config)

    # Ensure the database directory exists
    db_path = app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # Init extensions
    db.init_app(app)

    # Register blueprints
    from .routes.main import main_bp
    from .routes.health import health_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp)

    return app
