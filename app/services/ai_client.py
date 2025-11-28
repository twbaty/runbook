# app/services/ai_client.py
import requests
from flask import current_app

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


def call_llm(prompt: str) -> str:
    """
    Call the locally-selected Ollama model.
    """
    model = current_app.config.get("LOCAL_LLM_MODEL", "llama3.2:1b")

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": model, "prompt": prompt},
            timeout=20,
        )
        resp.raise_for_status()
    except Exception as e:
        print("LLM request failed:", e)
        return "UNKNOWN"

    # Ollama returns a streaming-like sequence of JSON objects.
    text = ""
    try:
        for line in resp.text.splitlines():
            if not line.strip():
                continue
            import json
            part = json.loads(line)
            text += part.get("response", "")
    except Exception as e:
        print("LLM parse error:", e)
        return "UNKNOWN"

    return text.strip()
