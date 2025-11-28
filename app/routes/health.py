# app/routes/health.py
from flask import Blueprint, jsonify
from ..services.ollama_manager import ensure_ollama_running, warm_model

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=["GET"])
def health_check():
    try:
        ensure_ollama_running()
        warmed = warm_model()
        return jsonify({
            "status": "ok",
            "ollama_running": True,
            "model_ready": warmed
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
