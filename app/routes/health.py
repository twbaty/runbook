# app/routes/health.py
from flask import Blueprint, jsonify
from ..services.ollama_manager import ensure_ollama_running, ping_model

health_bp = Blueprint("health", __name__)

@health_bp.route("/health")
def healthcheck():
    # Check Ollama
    ollama_ok = ensure_ollama_running()
    model_ok = ping_model()

    return jsonify({
        "status": "ok",
        "ollama_running": ollama_ok,
        "model_loaded": model_ok
    })
