# app/__init__.py
from flask import Flask
from .extensions import db
from .ollama_auto import pick_best_model  # OK
from .routes.main import main_bp          # <-- your web UI
from .routes.health import bp as health_bp      # <-- the /health endpoint

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)

    # ---- auto model selection ----
    selected_model, free_ram = pick_best_model()
    app.config["LOCAL_LLM_MODEL"] = selected_model
    app.config["LOCAL_FREE_RAM_GIB"] = free_ram

    # ---- register your existing blueprints ----
    app.register_blueprint(main_bp)      # <--- THIS brings back the web pages
    app.register_blueprint(health_bp)

    return app
