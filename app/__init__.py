from flask import Flask
from .ollama_auto import pick_best_model
from .routes.health import bp as health_bp

def create_app():
    app = Flask(__name__)

    # Determine best model + free RAM
    model_name, free_ram = pick_best_model()
    app.config["LOCAL_LLM_MODEL"] = model_name
    app.config["LOCAL_FREE_RAM_GIB"] = free_ram

    # Register blueprints
    app.register_blueprint(health_bp)

    return app
