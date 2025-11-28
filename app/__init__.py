from flask import Flask
from .ollama_auto import pick_best_model, warm_model

def create_app():
    app = Flask(__name__)

    selected_model, free_ram = pick_best_model()
    app.config["LOCAL_LLM_MODEL"] = selected_model
    app.config["LOCAL_FREE_RAM_GIB"] = free_ram

    warm_model(selected_model)

    return app
