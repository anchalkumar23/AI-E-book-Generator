from .base import KnowledgeProvider
from .duckduckgo import DuckDuckGoProvider
from .none import NoneProvider


def get_knowledge(name: str = "duckduckgo") -> KnowledgeProvider:
    """Phase 3 adds: if name == "zim": return ZimProvider()"""
    if name == "duckduckgo":
        return DuckDuckGoProvider()
    if name == "none":
        return NoneProvider()
    raise ValueError(f"unknown knowledge provider: {name}")
