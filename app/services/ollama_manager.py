# app/services/ollama_manager.py
import subprocess
import json
import time
import shutil

OLLAMA_HOST = "http://127.0.0.1:11434"
REQUIRED_MODEL = "llama3.1"


def _run_cmd(cmd: str):
    """Run shell command silently."""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


# ------------------------------------------------------------
# SERVICE DETECTION
# ------------------------------------------------------------
def systemd_service_exists() -> bool:
    """Return True if ollama.service exists in the user systemd tree."""
    result = _run_cmd("systemctl --user list-unit-files | grep -q ollama.service")
    return result.returncode == 0


def ollama_via_systemd_is_running() -> bool:
    """True if the systemd service is active."""
    result = _run_cmd("systemctl --user is-active ollama")
    return result.stdout.strip() == "active"


# ------------------------------------------------------------
# DIRECT MODE (curl installer)
# ------------------------------------------------------------
def ollama_binary_exists() -> bool:
    """True if the 'ollama' binary is available."""
    return shutil.which("ollama") is not None


def ollama_via_direct_is_running() -> bool:
    """Check if an Ollama server is already listening."""
    result = _run_cmd("pgrep -f 'ollama serve'")
    return result.returncode == 0


def start_ollama_direct():
    """Start Ollama in background using the binary directly."""
    print("⚠ Starting Ollama in direct mode...")
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    if not ollama_via_direct_is_running():
        raise RuntimeError("❌ Failed to start Ollama (direct mode)")
    print("✔ Ollama started (direct mode).")


# ------------------------------------------------------------
# ONE UNIFIED START FUNCTION
# ------------------------------------------------------------
def ensure_ollama_running():
    """Ensure Ollama is running, using systemd if available."""
    # 1) Systemd exists → use it
    if systemd_service_exists():
        if not ollama_via_systemd_is_running():
            print("⚠ Ollama is NOT running (systemd). Attempting to start...")
            result = _run_cmd("systemctl --user start ollama")
            if result.returncode != 0:
                raise RuntimeError("❌ Failed to start Ollama via systemd")
            print("✔ Ollama started (systemd).")
        else:
            print("✔ Ollama already running (systemd).")
        return

    # 2) Systemd missing → fall back to direct
    if not ollama_binary_exists():
        raise RuntimeError("❌ Ollama binary not found; cannot start.")

    if not ollama_via_direct_is_running():
        start_ollama_direct()
    else:
        print("✔ Ollama already running (direct mode).")


# ------------------------------------------------------------
# MODEL MANAGEMENT
# ------------------------------------------------------------
def list_models() -> list[str]:
    """Return list of installed models."""
    result = _run_cmd("ollama list --json")
    if result.returncode != 0:
        return []

    try:
        models = json.loads(result.stdout)
        return [m["name"] for m in models]
    except Exception:
        return []


def ensure_model_present(model: str = REQUIRED_MODEL):
    """Pull model if missing."""
    models = list_models()

    if model in models:
        print(f"✔ Model '{model}' already installed.")
        return

    print(f"⚠ Model '{model}' missing — pulling now...")
    result = _run_cmd(f"ollama pull {model}")
    if result.returncode != 0:
        raise RuntimeError(f"❌ Failed to pull model '{model}'")
    print(f"✔ Model '{model}' installed.")


# ------------------------------------------------------------
# WARM MODEL
# ------------------------------------------------------------
def warm_model(model: str = REQUIRED_MODEL):
    """Ping model so it loads into RAM."""
    import requests
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": model, "prompt": "ping"},
            timeout=10,
        )
        if resp.status_code == 200:
            print("🔥 Model warmed and ready.")
            return True
    except Exception:
        pass

    print("⚠ Model warm-up failed (cold start).")
    return False


# ------------------------------------------------------------
# THIS IS WHAT YOU CALL ON APP STARTUP
# ------------------------------------------------------------
def ensure_ollama_ready():
    ensure_ollama_running()
    ensure_model_present()
    warm_model()
