# app/services/ollama_manager.py
import subprocess
import json
import time
import requests

OLLAMA_HOST = "http://127.0.0.1:11434"
REQUIRED_MODEL = "llama3.1"


# ------------------------------
# Shell Helpers
# ------------------------------

def _run_cmd(cmd):
    """Run a shell command and capture output."""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


# ------------------------------
# Service Status
# ------------------------------

def ollama_is_running() -> bool:
    """Return True if Ollama service is running."""
    proc = _run_cmd("pgrep ollama")
    return proc.returncode == 0


def start_ollama():
    """Start Ollama if not running."""
    if not ollama_is_running():
        print("⚠ Ollama is NOT running. Attempting to start...")
        proc = _run_cmd("systemctl --user start ollama")

        # Wait briefly for it to come up
        time.sleep(2)

        if not ollama_is_running():
            raise RuntimeError("❌ Failed to start Ollama")
        print("✔ Ollama started successfully.")
    else:
        print("✔ Ollama is already running.")


# ------------------------------
# Model Helpers
# ------------------------------

def list_models() -> list[str]:
    """Return a list of installed Ollama models."""
    proc = _run_cmd("ollama list --json")
    if proc.returncode != 0:
        return []

    try:
        models = json.loads(proc.stdout)
        return [m["name"] for m in models]
    except Exception:
        return []


def ensure_model_present(model: str = REQUIRED_MODEL):
    """Pull the model if it is missing."""
    models = list_models()

    if model in models:
        print(f"✔ Model '{model}' already installed.")
        return

    print(f"⚠ Model '{model}' not found. Pulling now...")
    proc = _run_cmd(f"ollama pull {model}")
    if proc.returncode != 0:
        raise RuntimeError(f"❌ Failed to pull model '{model}'")
    print(f"✔ Model '{model}' downloaded and installed.")


# ------------------------------
# Model Ping + Warm
# ------------------------------

def ping_model(model: str = REQUIRED_MODEL) -> bool:
    """
    Send a tiny prompt to ensure Ollama + model both work.
    Returns True if healthy.
    """
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": model, "prompt": "ping"},
            timeout=6,
        )
        return resp.status_code == 200
    except Exception:
        return False


def ensure_ollama_running() -> bool:
    """
    Public-safe function used by health checks and warmups.
    Makes sure:
      1. Ollama service is running
      2. REQUIRED_MODEL is installed
    Returns True if ready.
    """
    try:
        start_ollama()
        ensure_model_present(REQUIRED_MODEL)
        return True
    except Exception as exc:
        print("❌ ensure_ollama_running failed:", exc)
        return False


def warm_model():
    """
    Ensure Ollama is running AND preload the model into RAM.
    Called automatically at app startup.
    """
    if ensure_ollama_running():
        print("🔥 Warming Ollama model...")
        if ping_model():
            print("✔ Model is warmed and ready.")
        else:
            print("⚠ Model ping failed — but service is running.")
