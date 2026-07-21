from .base import LlmProvider
from .groq import GroqProvider
from .ollama import OllamaProvider


def get_llm(name: str = "ollama", **kwargs) -> LlmProvider:
    """Adding a provider = one import + one line here."""
    if name == "ollama":
        return OllamaProvider(**kwargs)
    if name == "groq":
        return GroqProvider(**kwargs)
    raise ValueError(f"unknown llm provider: {name}")
