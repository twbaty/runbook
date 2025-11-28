# app/services/ai_client.py
import os
import json
import requests
from flask import current_app

def call_llm(prompt: str) -> str:
    """
    Calls OpenAI and forces strict JSON-only output.
    """
    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    # Force JSON-only responses so json.loads() never breaks
    system_msg = (
        "You must return ONLY valid JSON. "
        "No markdown. No code fences. No explanations. "
        "Just a JSON object."
    )

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "gpt-4.1-mini",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,   # deterministic so JSON stays stable
        },
        timeout=30,
    )

    resp.raise_for_status()
    data = resp.json()

    # Extract the model's response text
    output = data["choices"][0]["message"]["content"].strip()

    return output
