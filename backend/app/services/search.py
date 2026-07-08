from duckduckgo_search import DDGS


def _ddg(query: str, max_results: int) -> list[dict]:
    try:
        return list(DDGS().text(query, max_results=max_results))
    except Exception:
        return []


def research(topic: str) -> tuple[str, list[dict]]:
    """
    Multi-source research: general web + Wikipedia + facts/trivia.
    Returns (formatted_text_for_llm, sources_list).
    """
    seen_urls: set[str] = set()
    all_results: list[dict] = []

    queries = [
        (topic,                                   4),  # general web
        (f"{topic} site:wikipedia.org",           2),  # Wikipedia
        (f"{topic} facts history key information", 2),  # facts & trivia
    ]

    for query, limit in queries:
        for r in _ddg(query, limit):
            url = r.get("href", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(r)

    if not all_results:
        return "No research data available.", []

    text = "\n".join(f"- {r['title']}: {r['body']}" for r in all_results)
    sources = [{"title": r["title"], "url": r["href"]} for r in all_results if r.get("href")]
    return text, sources
