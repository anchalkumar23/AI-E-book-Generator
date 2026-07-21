"""Groq via its OpenAI-compatible HTTP API.

Uses httpx directly rather than the `groq` SDK: the SDK hung indefinitely on
create() here while a plain POST to the same endpoint returned in 0.7s. Talking
HTTP ourselves also drops a heavy dependency and matches the Ollama provider.
"""
import json
import os
from typing import Callable

import httpx

from .base import LlmProvider, LlmUnavailable

GROQ_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")


class GroqProvider(LlmProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def stream_json(self, prompt: str, on_token: Callable[[str], None]) -> dict:
        if not self.api_key:
            raise LlmUnavailable("No Groq API key set. Add one in Settings, or switch to Ollama.")

        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        full = ""
        try:
            with httpx.stream("POST", f"{GROQ_URL}/chat/completions",
                              json=body, headers=headers, timeout=180) as r:
                if r.status_code in (401, 403):
                    raise LlmUnavailable("Groq rejected the API key. Check it in Settings.")
                if r.status_code == 429:
                    raise LlmUnavailable("Groq rate limit reached. Wait a moment and retry.")
                if r.status_code == 404:
                    raise LlmUnavailable(
                        f"Groq model '{self.model}' not found. Change it in Settings."
                    )
                r.raise_for_status()

                for line in r.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload == "[DONE]":
                        break
                    token = json.loads(payload)["choices"][0]["delta"].get("content", "")
                    if token:
                        full += token
                        on_token(token)
        except httpx.ConnectError as e:
            raise LlmUnavailable("Can't reach Groq — check your internet connection.") from e
        except httpx.TimeoutException as e:
            raise LlmUnavailable("Groq timed out. Try again.") from e

        return json.loads(full)
