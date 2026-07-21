import json

from app.services.llm.base import LlmProvider

BLUEPRINT = {
    "writing_style": "plain", "tone": "warm", "target_audience": "all",
    "visual_style": "watercolor", "color_palette": "warm",
    "characters": [],
    "chapters": [{"number": 1, "title": "One", "summary": "s", "page_count": 1, "key_events": []}],
}
CHAPTER = {"pages": [{"page_number": 1, "heading": "H", "text": "Hello", "illustration": {}, "requires_real_person": False}]}


class FakeLlm(LlmProvider):
    """Returns canned JSON so the pipeline can be asserted without a real model."""

    def __init__(self):
        self.calls = 0

    def stream_json(self, prompt: str, on_token) -> dict:
        self.calls += 1
        payload = BLUEPRINT if self.calls == 1 else CHAPTER
        raw = json.dumps(payload)
        for ch in raw:
            on_token(ch)
        return payload


def test_pipeline_emits_expected_event_sequence(monkeypatch, tmp_path):
    from app.services import generator

    # This test runs without a session; provider resolution is covered in
    # test_settings_wiring.py.
    monkeypatch.setattr(generator, "setting", lambda session, key: "fake")
    monkeypatch.setattr(generator, "get_llm", lambda *a, **k: FakeLlm())
    monkeypatch.setattr(generator, "get_knowledge", lambda *a, **k: type("N", (), {"research": lambda self, t: ("none", [])})())
    monkeypatch.setattr(generator, "get_images", lambda *a, **k: type("P", (), {"generate": lambda self, p, b, n: None})())

    events: list[str] = []

    class FakeBook:
        id = 1
        title = "T"; prompt = "p"; book_type = "guide"; page_count = 1
        illustration_style = "watercolor"; use_research = False; writing_style = None

    monkeypatch.setattr(generator, "_save", lambda *a, **k: None)
    generator._generate(FakeBook(), None, lambda e: events.append(e["type"]))

    assert "progress" in events
    assert "page" in events
    assert events[-1] == "done"
