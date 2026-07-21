import json

import pytest

from app.services.llm.base import LlmProvider, stream_json_with_retry
from app.services.llm.factory import get_llm
from app.services.llm.groq import GroqProvider
from app.services.llm.ollama import OllamaProvider


def test_default_is_ollama():
    assert isinstance(get_llm("ollama"), OllamaProvider)


def test_groq_is_selectable():
    assert isinstance(get_llm("groq"), GroqProvider)


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="unknown llm provider"):
        get_llm("nope")


class FlakyLlm(LlmProvider):
    """Returns broken JSON on the first call, valid JSON on the second."""

    def __init__(self):
        self.calls = 0

    def stream_json(self, prompt, on_token):
        self.calls += 1
        if self.calls == 1:
            raise json.JSONDecodeError("bad", "{", 0)
        return {"ok": True}


class AlwaysBrokenLlm(LlmProvider):
    def stream_json(self, prompt, on_token):
        raise json.JSONDecodeError("bad", "{", 0)


def test_retries_once_on_invalid_json():
    llm = FlakyLlm()
    assert stream_json_with_retry(llm, "p", lambda _t: None) == {"ok": True}
    assert llm.calls == 2


def test_gives_up_after_one_retry():
    with pytest.raises(json.JSONDecodeError):
        stream_json_with_retry(AlwaysBrokenLlm(), "p", lambda _t: None)
