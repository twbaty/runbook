# app/services/ai_client.py
import os
import json
import requests
from flask import current_app

from .phi_scrub import scrub_text


# ======================================================
# LOCAL LLM (OLLAMA) CLIENT
# ======================================================

def _get_llm_base_url() -> str:
    """Return the local LLM server URL."""
    return current_app.config.get("LOCAL_LLM_BASE_URL", "http://localhost:11434")


def _get_llm_model() -> str:
    """Return the local LLM model name."""
    return current_app.config.get("LOCAL_LLM_MODEL", "llama3.1")


def call_llm(prompt: str) -> str:
    """
    Call a **local** LLM using Ollama.
    PHI is scrubbed before the request.
    """
    prompt_safe = scrub_text(prompt)

    base_url = _get_llm_base_url()
    model = _get_llm_model()

    # Ollama chat endpoint
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a security runbook assistant."},
            {"role": "user", "content": prompt_safe},
        ],
        "stream": False,
    }

    resp = requests.post(f"{base_url}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()

    data = resp.json()
    return data.get("message", {}).get("content", "").strip()



# ======================================================
# OPTIONAL: OPENAI FALLBACK (DISABLED BY DEFAULT)
# ======================================================
"""
Uncomment ONLY if you reinstate OpenAI usage *AND* have a BAA.
Otherwise leave disabled for PHI reasons.

from openai import OpenAI

def call_llm_openai(prompt: str) -> str:
    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    client = OpenAI(api_key=api_key)

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": scrub_text(prompt)}
        ]
    )
    return resp.choices[0].message.content
"""
