# app/__init__.py
from flask import Flask
from .config import Config
from .extensions import db, migrate
from .routes.main import main_bp

def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(main_bp)

    return app
