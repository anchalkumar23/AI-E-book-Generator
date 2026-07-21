import pytest


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_empty_library(client):
    r = client.get("/api/books/")
    assert r.status_code == 200
    assert r.json() == []


def test_list_returns_newest_first(client, book_factory):
    a = book_factory(title="First")
    b = book_factory(title="Second")
    ids = [b["id"] for b in client.get("/api/books/").json()]
    assert ids.index(b["id"]) < ids.index(a["id"])


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_sets_defaults(client):
    r = client.post("/api/books/", json={"title": "Defaults", "prompt": "P"})
    data = r.json()
    assert data["status"] == "generating"
    assert data["favorite"] is False
    assert data["progress"] == 0
    assert data["book_type"] == "tutorial"


def test_create_with_all_fields(client):
    payload = {
        "title": "Full Book",
        "prompt": "Detailed prompt",
        "book_type": "childrens",
        "page_count": 8,
        "illustration_style": "Watercolor",
        "cover_hue": 155,
    }
    r = client.post("/api/books/", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["book_type"] == "childrens"
    assert data["page_count"] == 8
    assert data["cover_hue"] == 155


def test_create_requires_title_and_prompt(client):
    assert client.post("/api/books/", json={"title": "No prompt"}).status_code == 422
    assert client.post("/api/books/", json={"prompt": "No title"}).status_code == 422


def test_create_rejects_invalid_book_type(client):
    r = client.post("/api/books/", json={"title": "T", "prompt": "P", "book_type": "INVALID"})
    assert r.status_code == 422


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_existing_book(client, book_factory):
    book = book_factory(title="Fetchable")
    r = client.get(f"/api/books/{book['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "Fetchable"


def test_get_nonexistent_book_returns_404(client):
    r = client.get("/api/books/99999")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


# ── Update ────────────────────────────────────────────────────────────────────

def test_mark_favorite(client, book_factory):
    book = book_factory()
    r = client.patch(f"/api/books/{book['id']}", json={"favorite": True})
    assert r.status_code == 200
    assert r.json()["favorite"] is True


def test_unmark_favorite(client, book_factory):
    book = book_factory()
    client.patch(f"/api/books/{book['id']}", json={"favorite": True})
    r = client.patch(f"/api/books/{book['id']}", json={"favorite": False})
    assert r.json()["favorite"] is False


def test_update_progress_and_status(client, book_factory):
    book = book_factory()
    r = client.patch(f"/api/books/{book['id']}", json={"progress": 60, "status": "done"})
    data = r.json()
    assert data["progress"] == 60
    assert data["status"] == "done"


def test_partial_update_does_not_reset_other_fields(client, book_factory):
    book = book_factory(title="Keep Me")
    client.patch(f"/api/books/{book['id']}", json={"favorite": True})
    r = client.patch(f"/api/books/{book['id']}", json={"progress": 50})
    data = r.json()
    assert data["favorite"] is True   # untouched
    assert data["title"] == "Keep Me"  # untouched
    assert data["progress"] == 50


def test_update_nonexistent_book_returns_404(client):
    r = client.patch("/api/books/99999", json={"favorite": True})
    assert r.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_removes_book(client, book_factory):
    book = book_factory()
    assert client.delete(f"/api/books/{book['id']}").status_code == 204
    assert client.get(f"/api/books/{book['id']}").status_code == 404


def test_delete_nonexistent_book_returns_404(client):
    assert client.delete("/api/books/99999").status_code == 404


def test_delete_does_not_affect_other_books(client, book_factory):
    a = book_factory(title="Keep")
    b = book_factory(title="Delete me")
    client.delete(f"/api/books/{b['id']}")
    ids = [b["id"] for b in client.get("/api/books/").json()]
    assert a["id"] in ids
    assert b["id"] not in ids
