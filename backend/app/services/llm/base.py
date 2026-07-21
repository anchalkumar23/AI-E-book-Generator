import json
from abc import ABC, abstractmethod
from typing import Callable


class LlmProvider(ABC):
    """Streams a JSON completion, emitting each token as it arrives."""

    @abstractmethod
    def stream_json(self, prompt: str, on_token: Callable[[str], None]) -> dict:
        ...


class LlmUnavailable(RuntimeError):
    """Raised with a message the user can act on."""


def stream_json_with_retry(
    provider: LlmProvider,
    prompt: str,
    on_token: Callable[[str], None],
    attempts: int = 2,
) -> dict:
    """Retries once when the model emits malformed JSON.

    Lives here rather than in each provider so every provider gets it for free.
    """
    for attempt in range(attempts):
        try:
            return provider.stream_json(prompt, on_token)
        except json.JSONDecodeError:
            if attempt == attempts - 1:
                raise
    raise AssertionError("unreachable")
