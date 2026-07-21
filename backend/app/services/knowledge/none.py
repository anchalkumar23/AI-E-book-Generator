from .base import NO_RESEARCH, KnowledgeProvider


class NoneProvider(KnowledgeProvider):
    def research(self, topic: str) -> tuple[str, list[dict]]:
        return NO_RESEARCH, []
