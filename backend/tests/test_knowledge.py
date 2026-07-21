from app.services.knowledge.base import NO_RESEARCH
from app.services.knowledge.duckduckgo import DuckDuckGoProvider
from app.services.knowledge.factory import get_knowledge
from app.services.knowledge.none import NoneProvider


def test_factory_selects_providers():
    assert isinstance(get_knowledge("duckduckgo"), DuckDuckGoProvider)
    assert isinstance(get_knowledge("none"), NoneProvider)


def test_none_provider_returns_empty():
    text, sources = NoneProvider().research("anything")
    assert sources == []
    assert "No research" in text


def test_scrape_failure_degrades_instead_of_raising(monkeypatch):
    """A flaky scraper must never kill a book."""
    provider = DuckDuckGoProvider()
    monkeypatch.setattr(provider, "_search", lambda q, n: (_ for _ in ()).throw(RuntimeError("ddg down")))
    text, sources = provider.research("Ancient Rome")
    assert sources == []
    assert "No research" in text


def test_malformed_hit_does_not_kill_the_book(monkeypatch):
    """A hit missing title/body must degrade, not raise.

    Indexing r['title'] would KeyError straight out of research() — past the
    try/except — and take the whole book down with it.
    """
    provider = DuckDuckGoProvider()
    monkeypatch.setattr(provider, "_search", lambda q, n: [{"href": "http://a.com"}])
    text, sources = provider.research("Ancient Rome")
    assert (text, sources) == (NO_RESEARCH, [])


def test_partial_hit_is_still_usable(monkeypatch):
    """Title but no body is still worth feeding to the model."""
    provider = DuckDuckGoProvider()
    monkeypatch.setattr(
        provider, "_search", lambda q, n: [{"href": "http://a.com", "title": "Rome"}]
    )
    text, sources = provider.research("Ancient Rome")
    assert "Rome" in text
    assert sources == [{"title": "Rome", "url": "http://a.com"}]
