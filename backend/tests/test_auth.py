import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app


@pytest.fixture
def client(monkeypatch):
    """Unauthenticated client with an isolated in-memory database.

    These tests send their own headers, so unlike conftest's `client` this one
    must NOT attach a token by default. It overrides get_session so the suite
    never reads the developer's real ebooks.db — otherwise these tests would
    fail on a clean checkout where that file doesn't exist.
    """
    monkeypatch.setenv("ENGINE_PORT", "12345")
    monkeypatch.setenv("ENGINE_TOKEN", "test-token-abc")

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        app.dependency_overrides[get_session] = lambda: session
        yield TestClient(app)
        app.dependency_overrides.clear()


def test_request_without_token_is_rejected(client):
    assert client.get("/api/books/").status_code == 401


def test_request_with_wrong_token_is_rejected(client):
    r = client.get("/api/books/", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_request_with_correct_token_is_allowed(client):
    r = client.get("/api/books/", headers={"Authorization": "Bearer test-token-abc"})
    assert r.status_code == 200


def test_cors_preflight_is_allowed_without_token(client):
    """A browser sends no Authorization on preflight.

    Rejecting it makes every request from the WebView fail as "Failed to fetch",
    which is what happened in the real app before this was fixed.
    """
    r = client.options(
        "/api/books/",
        headers={
            "Origin": "http://localhost:1420",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:1420"


def test_production_webview_origin_is_allowed(client):
    r = client.options(
        "/api/books/",
        headers={
            "Origin": "http://tauri.localhost",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.headers["access-control-allow-origin"] == "http://tauri.localhost"
