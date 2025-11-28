import subprocess
import psutil
import requests
import math

# Minimum realistic RAM required per parameter size (free RAM, not total)
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

def get_free_ram_gib():
    mem = psutil.virtual_memory()
    return mem.available / (1024 ** 3)

def list_local_models():
    try:
        result = subprocess.run(
            ["curl", "-s", "http://127.0.0.1:11434/api/tags"],
            capture_output=True,
            text=True
        )
        data = result.stdout
        import json
        parsed = json.loads(data)
        return parsed.get("models", [])
    except Exception as e:
        print("Error listing Ollama models:", e)
        return []

def extract_param_size(model_info):
    """Extract 'parameter_size' like '3B' or '8.0B' and normalize."""
    details = model_info.get("details", {})
    p = details.get("parameter_size")
    if not p:
        return None
    p = p.upper().replace("B", "").strip()
    try:
        val = float(p)
        return f"{val}B"
    except ValueError:
        return None

def pick_best_model():
    models = list_local_models()
    free_ram = get_free_ram_gib()

    candidates = []
    for m in models:
        param = extract_param_size(m)
        if not param:
            continue

        # Normalize like "3.0B" -> "3B"
        param_key = param.replace(".0B", "B")

        needed = MODEL_RAM_REQUIREMENTS_GIB.get(param_key)
        if needed is None:
            # Unknown sizes fall back to requiring free_ram >= model_size_in_bytes / 1e9 * 1.2
            needed = (m.get("size", 0) / (1024 ** 3)) * 1.2

        if free_ram >= needed:
            # Add as candidate (larger models get priority later)
            candidates.append((float(param_key.replace("B", "")), m))

    if not candidates:
        # Absolute fallback: pick smallest model installed
        smallest = sorted(models, key=lambda x: x.get("size", 9999999999))[0]
        return smallest.get("name"), free_ram

    # Pick the largest by parameter size
    _, best = sorted(candidates, key=lambda x: x[0], reverse=True)[0]
    return best.get("name"), free_ram


def warm_model(model_name):
    try:
        print(f"Warming model {model_name} ...")
        requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": model_name, "prompt": "hello"},
            timeout=10,
        )
        return True
    except Exception as e:
        print("Warm model error:", e)
        return False
