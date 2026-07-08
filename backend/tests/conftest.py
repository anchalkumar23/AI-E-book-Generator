import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool
from app.main import app
from app.database import get_session


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
def client_fixture(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
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
