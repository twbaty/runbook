# app/services/ollama_manager.py
import subprocess
import json
import time


OLLAMA_HOST = "http://127.0.0.1:11434"
REQUIRED_MODEL = "llama3.1"


def _run_cmd(cmd):
    """Run a shell command and capture output."""
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True
    )


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


def ensure_ollama_ready():
    """Top-level initializer: run once on Flask startup."""
    start_ollama()
    ensure_model_present(REQUIRED_MODEL)
