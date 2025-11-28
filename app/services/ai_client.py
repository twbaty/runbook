# app/services/ai_client.py
import os
import json
import requests

from flask import current_app

def call_llm(prompt: str) -> str:
    """
    Very simple wrapper. Replace with real client library.
    """
    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    # Pseudo-code. Swap for whichever model endpoint you're actually using.
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "gpt-4.1-mini",
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
