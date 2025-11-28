import subprocess
import psutil
import requests
import time
import json

# Minimum realistic free RAM needed per model family
MODEL_RAM_REQUIREMENTS_GIB = {
    "0.5B": 1.0,
    "1B":   1.5,
    "1.2B": 1.5,
    "2B":   2.5,
    "3B":   4.0,
    "4B":   5.0,
    "7B":   7.0,
    "8B":   8.5,
    "12B":  12.0,
    "13B":  13.0,
    "30B":  30.0,
}

# -----------------------------------------
# SYSTEM RAM CHECK
# -----------------------------------------
def get_free_ram_gib():
    mem = psutil.virtual_memory()
    return mem.available / (1024 ** 3)


# -----------------------------------------
# OLLAMA PROCESS CHECK
# -----------------------------------------
def ensure_ollama_running():
    """
    Starts Ollama if it's not running.
    Returns True when the Ollama API is reachable.
    """
    # First, check if it's responding
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=1)
        if r.status_code == 200:
            return True
    except Exception:
        pass

    # Not running → try starting it
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print("Failed to start Ollama:", e)
        return False

    # Wait for it to come online
    for _ in range(25):
        try:
            r = requests.get("http://127.0.0.1:11434/api/tags", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            time.sleep(0.2)

    print("Ollama failed to start.")
    return False


# -----------------------------------------
# MODEL LISTING
# -----------------------------------------
def list_local_models():
    """
    Wraps curl → returns [] if API is offline or returns malformed JSON.
    """
    try:
        result = subprocess.run(
            ["curl", "-s", "http://127.0.0.1:11434/api/tags"],
            capture_output=True,
            text=True
        )
        if not result.stdout:
            return []

        parsed = json.loads(result.stdout)
        return parsed.get("models", [])
    except Exception:
        return []


# -----------------------------------------
# PARAMETER SIZE EXTRACTION
# -----------------------------------------
def extract_param_size(model_info):
    """
    Extracts sizes like '1B', '1.2B', '8B', etc.
    Returns normalized form '2B', '3B', '8B', etc.
    """
    details = model_info.get("details", {})
    p = details.get("parameter_size")
    if not p:
        return None

    p = p.upper().replace("B", "").strip()

    try:
        val = float(p)
        # Normalize: 3.0 → "3B"
        return f"{int(val)}B" if val.is_integer() else f"{val}B"
    except Exception:
        return None


# -----------------------------------------
# MODEL SELECTION
# -----------------------------------------
def pick_best_model():
    """
    Selects the largest local Ollama model that fits into available RAM.
    Returns (model_name, free_ram_gib).
    """
    models = list_local_models()
    free_ram = get_free_ram_gib()

    if not models:
        return None, free_ram

    candidates = []

    for m in models:
        param = extract_param_size(m)
        if not param:
            continue

        needed = MODEL_RAM_REQUIREMENTS_GIB.get(param, None)

        # If size unknown → estimate RAM need based on file size
        if needed is None:
            needed = (m.get("size", 0) / (1024 ** 3)) * 1.3

        if free_ram >= needed:
            num = float(param.replace("B", ""))
            candidates.append((num, m))

    if not candidates:
        # Fall back to smallest installed model
        smallest = sorted(models, key=lambda x: x.get("size", 999999999))[0]
        return smallest.get("name"), free_ram

    # Select largest that fits
    _, best = sorted(candidates, key=lambda x: x[0], reverse=True)[0]
    return best.get("name"), free_ram


# -----------------------------------------
# OPTIONAL: PRELOAD
# -----------------------------------------
def warm_model(model_name):
    """
    Sends a small prompt to preload the model.
    Does not crash the app if Ollama is cold.
    """
    try:
        requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": model_name, "prompt": "hello"},
            timeout=10,
        )
        return True
    except Exception:
        return False
