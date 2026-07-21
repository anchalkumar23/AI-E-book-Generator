"""Proves the Settings table actually drives the generator.

Without these tests the settings router would be decorative: it would write rows
that nothing ever reads.
"""
import json

from app.models.setting import Setting
from app.services.config import setting
from app.services.llm.base import LlmProvider

BLUEPRINT = {
    "writing_style": "plain", "tone": "warm", "target_audience": "all",
    "visual_style": "watercolor", "color_palette": "warm",
    "characters": [],
    "chapters": [{"number": 1, "title": "One", "summary": "s", "page_count": 1, "key_events": []}],
}
CHAPTER = {"pages": [{"page_number": 1, "heading": "H", "text": "Hello",
                      "illustration": {}, "requires_real_person": False}]}


class FakeLlm(LlmProvider):
    """Returns canned JSON so the pipeline can run without a real model."""

    def __init__(self):
        self.calls = 0

    def stream_json(self, prompt: str, on_token) -> dict:
        self.calls += 1
        payload = BLUEPRINT if self.calls == 1 else CHAPTER
        for ch in json.dumps(payload):
            on_token(ch)
        return payload


class FakeBook:
    id = 1
    title = "T"; prompt = "p"; book_type = "guide"; page_count = 1
    illustration_style = "watercolor"; use_research = False; writing_style = None


def test_db_row_is_used(session):
    session.add(Setting(key="llm_provider", value="groq"))
    session.commit()
    assert setting(session, "llm_provider") == "groq"


def test_default_when_no_row_and_no_env(session, monkeypatch):
    # Groq by default: it runs in the cloud, so generation doesn't need the
    # ~5 GB of free RAM a local 8B model wants.
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert setting(session, "llm_provider") == "groq"


def test_env_var_used_when_no_row(session, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    assert setting(session, "llm_provider") == "groq"


def test_db_row_beats_env_var(session, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    session.add(Setting(key="llm_provider", value="ollama"))
    session.commit()
    assert setting(session, "llm_provider") == "ollama"


def test_generator_resolves_llm_provider_from_settings(session, monkeypatch):
    """The whole point: a provider stored in Settings reaches get_llm."""
    from app.services import generator

    session.add(Setting(key="llm_provider", value="groq"))
    session.commit()

    # **kwargs: the generator passes each provider its own settings (api_key,
    # model), which is what stops the Settings screen being decorative.
    seen: list[str] = []
    monkeypatch.setattr(generator, "get_llm",
                        lambda name, **kw: seen.append(name) or FakeLlm())
    monkeypatch.setattr(generator, "get_knowledge",
                        lambda name, **kw: type("N", (), {"research": lambda self, t: ("none", [])})())
    monkeypatch.setattr(generator, "get_images",
                        lambda name, **kw: type("P", (), {"generate": lambda self, p, b, n: None})())
    monkeypatch.setattr(generator, "_save", lambda *a, **k: None)

    generator._generate(FakeBook(), session, lambda e: None)

    assert seen == ["groq"]


def test_generator_passes_credentials_to_providers(session, monkeypatch):
    """A key saved in Settings must actually reach the provider."""
    from app.services import generator

    session.add(Setting(key="groq_api_key", value="gsk_from_settings"))
    session.add(Setting(key="image_provider", value="huggingface"))
    session.add(Setting(key="hf_token", value="hf_from_settings"))
    session.commit()

    got: dict = {}
    monkeypatch.setattr(generator, "get_llm",
                        lambda name, **kw: got.update(llm=kw) or FakeLlm())
    monkeypatch.setattr(generator, "get_knowledge",
                        lambda name, **kw: type("N", (), {"research": lambda self, t: ("none", [])})())
    monkeypatch.setattr(generator, "get_images",
                        lambda name, **kw: got.update(img=kw) or
                        type("P", (), {"generate": lambda self, p, b, n: None})())
    monkeypatch.setattr(generator, "_save", lambda *a, **k: None)

    generator._generate(FakeBook(), session, lambda e: None)

    assert got["llm"]["api_key"] == "gsk_from_settings"
    assert got["img"]["token"] == "hf_from_settings"
