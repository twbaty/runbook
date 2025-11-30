# app/__init__.py
from flask import Flask
from .config import Config
from .extensions import db
from .routes.main import main_bp
from .routes.health import health_bp

def create_app():
    app = Flask(__name__, instance_relative_config=False)

    app.config.from_object(Config)

    db.init_app(app)

    # Ensure DB is created in the *correct path*, not cwd
    with app.app_context():
        db.create_all()

    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp, url_prefix="/health")

    return app
