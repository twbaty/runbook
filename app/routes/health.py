# app/routes/health.py
from flask import Blueprint, jsonify
from ..services.ollama_manager import ollama_is_running, warm_model

health_bp = Blueprint("health", __name__)

@health_bp.route("/health")
def health_check():
    return jsonify({
        "status": "ok",
        "ollama_running": ollama_is_running(),
        "model_ready": warm_model(),
    })
