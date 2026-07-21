import httpx
import pytest

from app.services.images.factory import get_images
from app.services.images.huggingface import HuggingFaceProvider
from app.services.images.placeholder import PlaceholderProvider


def test_factory_returns_placeholder():
    assert isinstance(get_images("placeholder"), PlaceholderProvider)


def test_factory_returns_huggingface():
    assert isinstance(get_images("huggingface"), HuggingFaceProvider)


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        get_images("nope")


def test_placeholder_generates_no_image_but_does_not_fail():
    assert PlaceholderProvider().generate("a castle at dusk", 1, 1) is None


def test_huggingface_without_token_makes_no_request(monkeypatch):
    """An unconfigured install must cost nothing — not one request per page."""
    def explode(*a, **k):
        raise AssertionError("no HTTP call should happen without a token")

    monkeypatch.setattr(httpx, "post", explode)
    assert HuggingFaceProvider(token="").generate("a castle", 1, 1) is None


def test_huggingface_network_error_returns_none(monkeypatch):
    """A missing illustration must never fail the book."""
    monkeypatch.setattr(httpx, "post", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("down")))
    assert HuggingFaceProvider(token="hf_x").generate("a castle", 1, 1) is None


def test_huggingface_saves_image_and_returns_relative_path(monkeypatch, tmp_path):
    """The path must stay engine-relative — the port changes every launch."""
    monkeypatch.setattr("app.services.images.huggingface.STATIC_DIR", tmp_path)
    monkeypatch.setattr(
        httpx, "post",
        lambda *a, **k: httpx.Response(
            200, headers={"content-type": "image/jpeg"}, content=b"\xff\xd8fake",
        ),
    )
    url = HuggingFaceProvider(token="hf_x").generate("a castle", 7, 3)

    assert url == "/static/images/7/3.jpg"
    assert not url.startswith("http")  # an absolute URL would break next launch
    assert (tmp_path / "images" / "7" / "3.jpg").read_bytes() == b"\xff\xd8fake"
