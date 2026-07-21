def test_create_and_list_chat(client):
    created = client.post("/api/chats/", json={"title": "Ancient Rome"})
    assert created.status_code == 201
    assert created.json()["title"] == "Ancient Rome"

    listed = client.get("/api/chats/")
    assert listed.status_code == 200
    assert any(c["title"] == "Ancient Rome" for c in listed.json())


def test_append_and_read_messages(client):
    chat_id = client.post("/api/chats/", json={"title": "T"}).json()["id"]
    client.post(f"/api/chats/{chat_id}/messages",
                json={"role": "user", "content": "Write a book"})
    msgs = client.get(f"/api/chats/{chat_id}/messages").json()
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Write a book"


def test_delete_chat_removes_it_and_its_messages(client):
    chat_id = client.post("/api/chats/", json={"title": "Bye"}).json()["id"]
    client.post(f"/api/chats/{chat_id}/messages", json={"role": "user", "content": "hi"})

    assert client.delete(f"/api/chats/{chat_id}").status_code == 204
    assert chat_id not in [c["id"] for c in client.get("/api/chats/").json()]
    assert client.get(f"/api/chats/{chat_id}/messages").json() == []


def test_message_on_missing_chat_is_404(client):
    r = client.post("/api/chats/999/messages", json={"role": "user", "content": "x"})
    assert r.status_code == 404


def test_settings_returns_defaults_then_persists_updates(client):
    defaults = client.get("/api/settings/")
    assert defaults.status_code == 200
    assert defaults.json()["llm_provider"] == "groq"

    # Written value must differ from the default, or this proves nothing.
    updated = client.put("/api/settings/", json={"llm_provider": "ollama", "bogus": "x"})
    assert updated.status_code == 200
    assert updated.json()["llm_provider"] == "ollama"
    assert "bogus" not in updated.json()

    assert client.get("/api/settings/").json()["llm_provider"] == "ollama"


def test_settings_shows_values_that_came_from_env(client, monkeypatch):
    """The Settings form must show the effective key, not a blank.

    Showing a blank meant saving the form wrote "" into the DB, where it beats
    the env var — silently breaking generation for anyone using a .env.
    """
    monkeypatch.setenv("GROQ_API_KEY", "gsk_from_env")
    assert client.get("/api/settings/").json()["groq_api_key"] == "gsk_from_env"


def test_saving_settings_does_not_wipe_an_env_key(client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_from_env")

    form = client.get("/api/settings/").json()        # what the UI loads
    saved = client.put("/api/settings/", json=form)   # user hits Save unchanged

    assert saved.json()["groq_api_key"] == "gsk_from_env"
