"""Resolves runtime settings: DB value -> env var -> default.

The settings router writes to the `setting` table; the generator reads through
here. Without this the Settings UI would be decorative.
"""
import os

from sqlmodel import Session

from ..models.setting import Setting

# Groq by default: it runs in the cloud, so generation doesn't need the ~5 GB of
# free RAM a local 8B model wants. Ollama stays available for offline use.
DEFAULTS = {
    "llm_provider": "groq",
    "groq_model": "llama-3.3-70b-versatile",
    "ollama_model": "llama3.1",
    "groq_api_key": "",
    "knowledge_provider": "duckduckgo",
    # Hugging Face free tier; returns None instantly without HF_TOKEN, so an
    # unconfigured install costs nothing. Pollinations moved to paid credits in
    # 2026 (anonymous requests 402) and is kept only for those with a key.
    "image_provider": "huggingface",
    "hf_token": "",
}


def setting(session: Session, key: str) -> str:
    row = session.get(Setting, key)
    if row and row.value:
        return row.value
    return os.getenv(key.upper(), DEFAULTS.get(key, ""))
