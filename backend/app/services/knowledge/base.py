from abc import ABC, abstractmethod

NO_RESEARCH = "No research data available."


class KnowledgeProvider(ABC):
    """Returns (facts_for_the_prompt, sources_to_cite)."""

    @abstractmethod
    def research(self, topic: str) -> tuple[str, list[dict]]:
        ...
