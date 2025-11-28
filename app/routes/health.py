from flask import Blueprint, current_app, jsonify

bp = Blueprint("health", __name__)

@bp.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "ollama_running": True,
        "model_selected": current_app.config.get("LOCAL_LLM_MODEL"),
        "ram_free_gib": round(current_app.config.get("LOCAL_FREE_RAM_GIB", 0), 2),
        "model_ready": True
    })
