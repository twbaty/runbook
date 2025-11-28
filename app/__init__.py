# app/__init__.py
import os
from flask import Flask
from dotenv import load_dotenv

from .config import Config
from .extensions import db, migrate
from .routes.main import main_bp


# app/__init__.py

import os
from dotenv import load_dotenv

# load secrets
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".secrets"))
load_dotenv()

from flask import Flask
from .config import Config
from .extensions import db, migrate
from .routes.main import main_bp

# NEW:
from .services.ollama_manager import ensure_ollama_running


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # NEW: Ensure Ollama is running BEFORE anything else loads
    try:
        ensure_ollama_running()
    except Exception as e:
        print(str(e))
        print("Flask will exit now.")
        raise SystemExit(1)

    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(main_bp)

    return app
