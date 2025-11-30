# app/__init__.py
from flask import Flask
from .config import Config
from .extensions import db
from .routes.main import main_bp
from .routes.health import health_bp

def create_app():
    # Do NOT use instance_relative_config — it causes DB path confusion
    app = Flask(__name__, instance_relative_config=False)

    # Load your Config() class (contains your correct DB_PATH)
    app.config.from_object(Config)

    # Initialize SQLAlchemy
    db.init_app(app)

    # Ensure the database is created in the CORRECT project root
    with app.app_context():
        db.create_all()

    # Register routes
    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp, url_prefix="/health")

    return app
