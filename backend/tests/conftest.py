import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool
from app.main import app
from app.database import get_session


@pytest.fixture(autouse=True)
def no_real_generation(monkeypatch):
    """Stop tests from generating real books.

    POST /api/books schedules run_generation as a BackgroundTask, and TestClient
    runs background tasks synchronously — so without this every test that creates
    a book would hit the real LLM and the live web, hanging the suite.
    The pipeline itself is covered directly in test_generator_events.py.
    """
    monkeypatch.setattr("app.routers.books.run_generation", lambda *a, **k: None)


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session, monkeypatch):
    """An authenticated client.

    Every request needs a bearer token now (see app/auth.py), so set a known
    token and send it by default. Auth itself is covered in test_auth.py.
    """
    token = "test-token"
    monkeypatch.setenv("ENGINE_TOKEN", token)
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app, headers={"Authorization": f"Bearer {token}"})
    app.dependency_overrides.clear()


@pytest.fixture(name="book_factory")
def book_factory_fixture(client):
    """Creates books via the API; returns the response JSON."""
    def _make(**overrides):
        payload = {"title": "Test Book", "prompt": "A test prompt", **overrides}
        r = client.post("/api/books/", json=payload)
        assert r.status_code == 201
        return r.json()
    return _make
