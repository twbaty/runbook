from flask import Flask
from .config import Config
from .extensions import db   # SQLAlchemy()
from .routes.main import main_bp
from .routes.health import health_bp

def create_app():
    # No instance-relative magic, no fallback config paths
    app = Flask(
        __name__,
        instance_relative_config=False
    )

    # Load config object explicitly
    app.config.from_object(Config)

    # Initialize SQLAlchemy with the correct DB path
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp, url_prefix="/health")

    return app
