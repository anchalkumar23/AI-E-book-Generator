from duckduckgo_search import DDGS

from .base import NO_RESEARCH, KnowledgeProvider


class DuckDuckGoProvider(KnowledgeProvider):
    """Temporary default. Replaced by ZimProvider in Phase 3."""

    def _search(self, query: str, max_results: int) -> list[dict]:
        return list(DDGS().text(query, max_results=max_results))

    def research(self, topic: str) -> tuple[str, list[dict]]:
        queries = [
            (topic, 4),
            (f"{topic} site:wikipedia.org", 2),
            (f"{topic} facts history key information", 2),
        ]
        seen: set[str] = set()
        results: list[dict] = []

        for query, limit in queries:
            try:
                hits = self._search(query, limit)
            except Exception:
                continue  # never let a flaky scraper kill a book
            for r in hits:
                url = r.get("href", "")
                if url and url not in seen:
                    seen.add(url)
                    results.append(r)

        # A hit with neither title nor body tells the model nothing. Drop it, and
        # read every field with .get(): a KeyError here would escape the try/except
        # above and kill the book, which is exactly what this class must prevent.
        usable = [r for r in results if r.get("title") or r.get("body")]
        if not usable:
            return NO_RESEARCH, []

        text = "\n".join(f"- {r.get('title', '')}: {r.get('body', '')}" for r in usable)
        sources = [{"title": r.get("title", ""), "url": r["href"]} for r in usable]
        return text, sources
