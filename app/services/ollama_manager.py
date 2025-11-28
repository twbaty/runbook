# app/services/ollama_manager.py
import subprocess
import json
import time
import psutil   # new dependency (pip install psutil)

OLLAMA_HOST = "http://127.0.0.1:11434"

# Auto-selected at runtime
SELECTED_MODEL = None


# ----------------------------
# Helpers
# ----------------------------
def _run_cmd(cmd):
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True
    )


def ollama_is_running() -> bool:
    proc = _run_cmd("pgrep ollama")
    return proc.returncode == 0


def start_ollama_direct():
    """Start Ollama using direct binary invocation."""
    if ollama_is_running():
        print("✔ Ollama already running (direct).")
        return True

    print("⚠ Starting Ollama (direct mode)...")
    proc = _run_cmd("ollama serve &")
    time.sleep(2)

    if not ollama_is_running():
        print("❌ Failed to start Ollama.")
        return False

    print("✔ Ollama started.")
    return True


def list_models() -> list[str]:
    proc = _run_cmd("ollama list --json")
    if proc.returncode != 0:
        return []

    try:
        return [m["name"] for m in json.loads(proc.stdout)]
    except Exception:
        return []


# ----------------------------
# RAM-based model selection
# ----------------------------
def pick_best_model():
    """Select largest model that fits into RAM."""

    total_gb = psutil.virtual_memory().total / (1024 ** 3)
    print(f"📦 Total RAM detected: {total_gb:.1f} GB")

    if total_gb < 2:
        return "llama3.2:1b"
    elif total_gb < 4:
        return "llama3.2:3b"
    elif total_gb < 8:
        return "llama3.1"
    else:
        return "llama3.1"


def ensure_model_present(model: str):
    installed = list_models()
    if model in installed:
        print(f"✔ Model '{model}' already installed.")
        return

    print(f"⚠ Model '{model}' missing — pulling...")
    proc = _run_cmd(f"ollama pull {model}")
    if proc.returncode != 0:
        raise RuntimeError(f"❌ Failed to pull model '{model}'")

    print("✔ Model downloaded.")


def warm_model(model: str):
    """Tests if the model can successfully answer a 1-token query."""
    import requests

    try:
        r = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": model, "prompt": "ping"},
            timeout=12,
        )
        if r.status_code == 200:
            print("🔥 Model warm.")
            return True

        print(f"⚠ Warm-up failed: {r.text}")
        return False

    except Exception as e:
        print(f"❌ Warm-up error: {e}")
        return False


# ----------------------------
# Main initializer
# ----------------------------
def initialize_ollama():
    global SELECTED_MODEL

    # Start Ollama
    start_ollama_direct()

    # Choose correct model
    SELECTED_MODEL = pick_best_model()
    print(f"👉 Using auto-selected model: {SELECTED_MODEL}")

    # Ensure installed
    ensure_model_present(SELECTED_MODEL)

    # Warm model
    warm_model(SELECTED_MODEL)

    return SELECTED_MODEL
