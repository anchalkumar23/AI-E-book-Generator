import os, json, httpx
from typing import Callable
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL",   "llama-3.3-70b-versatile")
OLLAMA_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL",   "llama3.2")


def _groq(prompt: str) -> str:
    res = Groq(api_key=GROQ_API_KEY).chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    return res.choices[0].message.content


def _ollama(prompt: str) -> str:
    res = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "format": "json", "stream": False},
        timeout=180,
    )
    res.raise_for_status()
    return res.json()["response"]


def generate_json(prompt: str) -> dict:
    raw = _groq(prompt) if GROQ_API_KEY else _ollama(prompt)
    return json.loads(raw)


def stream_json(prompt: str, on_token: Callable[[str], None]) -> dict:
    """Stream tokens from Groq, call on_token with each chunk, return parsed JSON."""
    if not GROQ_API_KEY:
        result = _ollama(prompt)
        return json.loads(result)

    stream = Groq(api_key=GROQ_API_KEY).chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,
        stream=True,
    )
    full = ""
    for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            full += token
            on_token(token)
    return json.loads(full)
