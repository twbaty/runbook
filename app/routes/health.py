# app/routes/health.py
from flask import Blueprint, jsonify, current_app

health_bp = Blueprint("health", __name__)

@health_bp.route("/")
def health():
    return jsonify({
        "status": "ok",
        "ollama_running": current_app.config.get("OLLAMA_RUNNING", True),
        "model_selected": current_app.config.get("LOCAL_LLM_MODEL"),
        "ram_free_gib": round(current_app.config.get("LOCAL_FREE_RAM_GIB", 0), 2),
        "model_ready": current_app.config.get("MODEL_READY", True)
    })
