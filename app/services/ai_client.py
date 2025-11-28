# app/services/ai_client.py
import os
import json
import requests
from flask import current_app

from .phi_scrub import scrub_text


def _get_llm_base_url() -> str:
    # Local LLM (Ollama) default
    return current_app.config.get("LOCAL_LLM_BASE_URL", "http://localhost:11434")


def _get_llm_model() -> str:
    # Default local model name
    return current_app.config.get("LOCAL_LLM_MODEL", "llama3.1")


def call_llm(prompt: str) -> str:
    """
    Call a local LLM (e.g., Ollama) instead of OpenAI.
    PHI/PII is scrubbed BEFORE it is sent to the model.
    """
    base_url = _get_llm_base_url()
    model = _get_llm_model()

    # Scrub PHI/PII from the prompt before sending anywhere
    safe_prompt = scrub_text(prompt)

    # Ollama chat API
    url = f"{base_url}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful security runbook assistant."},
            {"role": "user", "content": safe_prompt},
        ],
        "stream": False,
    }

    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    # Ollama returns content in: data["message"]["content"]
    msg = data.get("message", {}).get("content", "")
    return msg.strip()
