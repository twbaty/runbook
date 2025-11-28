from flask import Flask
from .config import Config
from .extensions import db, migrate
from .routes.main import main_bp
from .routes.health import health_bp

# NEW IMPORTS (corrected)
from .services.ollama_manager import ensure_ollama_running, warm_model


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp)

    # ---- OLLAMA INIT ----
    ensure_ollama_running()
    warm_model()
    # ---------------------

    return app
