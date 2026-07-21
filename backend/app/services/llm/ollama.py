import json
import os
from typing import Callable

import httpx

from .base import LlmProvider, LlmUnavailable

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class OllamaProvider(LlmProvider):
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1")

    def stream_json(self, prompt: str, on_token: Callable[[str], None]) -> dict:
        body = {"model": self.model, "prompt": prompt, "format": "json", "stream": True}
        full = ""
        try:
            with httpx.stream("POST", f"{OLLAMA_URL}/api/generate", json=body, timeout=600) as r:
                if r.status_code == 404:
                    raise LlmUnavailable(
                        f"Model '{self.model}' not found. Run: ollama pull {self.model}"
                    )
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        full += token
                        on_token(token)
        except httpx.ConnectError as e:
            raise LlmUnavailable("Ollama isn't running — start it and try again.") from e
        return json.loads(full)
