# app/services/ollama_manager.py
import subprocess
import time
import requests

OLLAMA_URL = "http://127.0.0.1:11434"


def is_ollama_running() -> bool:
    """
    Check if Ollama API is responding.
    """
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1)
        return r.status_code == 200
    except Exception:
        return False


def start_ollama() -> bool:
    """
    Attempt to start Ollama in the background.
    Works if Ollama is installed normally on Linux.
    """
    try:
        # Start Ollama daemon
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Give it time to initialize
        for _ in range(20):
            if is_ollama_running():
                return True
            time.sleep(0.3)

        return False

    except Exception as e:
        print("ERROR starting Ollama:", e)
        return False


def ensure_ollama_running():
    """
    Ensures Ollama is up.
    If not, tries to start it.
    Raises RuntimeError if unsuccessful.
    """
    if is_ollama_running():
        print("✔ Ollama is already running.")
        return

    print("⚠ Ollama is NOT running. Attempting to start...")
    if not start_ollama():
        raise RuntimeError(
            "❌ Ollama could not be started. "
            "Start it manually with 'ollama serve'."
        )

    print("✔ Ollama started successfully.")
