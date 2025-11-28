import subprocess
import psutil
import requests
import json
import time

# Hard lower limits based on real-world Ollama behavior
MODEL_RAM_REQUIREMENTS_GIB = {
    "0.5B": 1.0,
    "1B":   1.5,
    "1.2B": 1.5,
    "2B":   2.8,
    "3B":   4.0,
    "4B":   5.5,
    "7B":   8.0,
    "8B":   10.0,   # ← bump to prevent false positives
    "12B":  14.0,
    "13B":  15.0,
    "30B":  32.0,
}

def get_allocatable_ram_gib():
    """Return realistic allocatable RAM, not optimistic Linux numbers."""
    vm = psutil.virtual_memory()

    # More conservative than vm.available
    allocatable = (
        vm.available
        - vm.buffers
        - vm.shared
        - (0.10 * vm.total)   # subtract 10% safety margin
    )

    gib = max(allocatable / (1024 ** 3), 0)
    return round(gib, 2)

def list_local_models():
    try:
        out = subprocess.run(
            ["curl", "-s", "http://127.0.0.1:11434/api/tags"],
            text=True, capture_output=True
        )
        return json.loads(out.stdout).get("models", [])
    except:
        return []

def extract_param_size(model):
    details = model.get("details", {})
    p = details.get("parameter_size")
    if not p:
        return None
    p = p.upper().replace("B", "").strip()
    try:
        return f"{float(p)}B"
    except:
        return None

def test_load_model(name):
    """Try a tiny test generation to confirm the model is genuinely loadable."""
    try:
        res = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": name, "prompt": "hi"},
            timeout=4
        )
        if res.status_code != 200:
            return False
        data = res.json()
        if "error" in data:
            return False
        return True
    except:
        return False

def pick_best_model():
    models = list_local_models()
    alloc_ram = get_allocatable_ram_gib()

    candidates = []
    for m in models:
        param = extract_param_size(m)
        if not param:
            continue

        param_key = param.replace(".0B", "B")
        needed = MODEL_RAM_REQUIREMENTS_GIB.get(param_key)

        # If unknown param size, fail-safe to requiring full model size
        if needed is None:
            needed = (m.get("size", 0) / (1024**3)) * 1.5

        # Only consider if allocatable RAM is enough
        if alloc_ram >= needed:
            candidates.append((float(param_key.replace("B", "")), m))

    # If nothing fits conservative RAM limits → pick smallest model
    if not candidates:
        smallest = sorted(models, key=lambda x: x.get("size", 999999))[0]
        name = smallest.get("name")
        return name, alloc_ram

    # Try largest candidates first
    for _, m in sorted(candidates, key=lambda x: x[0], reverse=True):
        name = m.get("name")

        # Do NOT trust RAM alone — confirm with a real test load
        if test_load_model(name):
            return name, alloc_ram

    # If all test loads failed, fallback
    smallest = sorted(models, key=lambda x: x.get("size", 999999))[0]
    return smallest.get("name"), alloc_ram
