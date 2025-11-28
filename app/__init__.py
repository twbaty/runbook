from flask import Flask
from .ollama_auto import ensure_ollama_running, pick_best_model

def create_app():
    # 1) Ensure Ollama daemon is running BEFORE anything else
    ensure_ollama_running()

    # 2) Now we can safely detect RAM and pick a model
    selected_model, free_ram = pick_best_model()

    app = Flask(__name__)
    app.config["LOCAL_LLM_MODEL"] = selected_model
    app.config["LOCAL_LLM_RAM"] = free_ram

    # Register blueprints
    from .routes.health import health_bp
    from .routes.generate import generate_bp
    app.register_blueprint(health_bp)
    app.register_blueprint(generate_bp)

    return app
