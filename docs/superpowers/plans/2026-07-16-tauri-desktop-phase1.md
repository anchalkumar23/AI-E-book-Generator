# Tauri Desktop Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Pageforge into a single offline-first Tauri desktop app where a thin Rust shell supervises the existing Python engine, and a ChatGPT-style React UI drives live book generation.

**Architecture:** Rust/Tauri owns only the window and process lifecycle. It spawns the Python FastAPI engine as a child process, reads a one-line JSON handshake (`{ready, port, token}`) from its stdout, and hands `{port, token}` to the WebView. All AI generation, RAG, and future PDF/image work stays in Python, reached over loopback HTTP + WebSocket with bearer-token auth. Provider ABCs (LLM/Knowledge/Image) are the seams for adding ZIM and FLUX later.

**Tech Stack:** Tauri 2.11.5, `tauri-plugin-shell`, React 19 + Vite 6 + TypeScript, FastAPI + uvicorn + SQLModel (existing), rusqlite not used (Python owns SQLite), PyInstaller for bundling, Ollama (default) / Groq (opt-in).

**Spec:** `docs/superpowers/specs/2026-07-15-tauri-desktop-migration-design.md` (v2, approved)

---

## A note for the engineer

The project owner **does not know Rust or Tauri**. Every Rust task below explains what the code does in plain language. Keep that up in commit messages and comments.

**The owner handles all git themselves.** No task in this plan runs a git command. Tasks end with a **Checkpoint** telling the owner what to review and commit. Never run `git` yourself.

---

## File Structure

What each new/changed file is responsible for. Nothing else gets touched.

### Rust shell — `src-tauri/` (4 source files, deliberately tiny)

| File | Responsibility |
| --- | --- |
| `src/main.rs` | Tauri builder, plugin init, kick off engine, kill child on exit |
| `src/engine.rs` | Spawn Python (dev: venv, prod: sidecar), parse handshake, 30s timeout |
| `src/state.rs` | `EngineState` — holds `{port, token}` + the child handle |
| `src/commands.rs` | `engine_info()` command exposed to the UI |
| `Cargo.toml` | Rust deps |
| `tauri.conf.json` | Window config, `externalBin` sidecar entry |
| `capabilities/default.json` | Shell permissions (spawn/kill/execute) |
| `binaries/` | PyInstaller output lands here (gitignored) |

### Python engine — `backend/app/` (refactor, not rewrite)

| File | Responsibility |
| --- | --- |
| `engine.py` | **NEW** — pick free port, mint token, stdin watchdog, run uvicorn |
| `auth.py` | **NEW** — bearer-token HTTP middleware + WS token check |
| `main.py` | **MODIFIED** — loopback bind, token middleware, Tauri CORS, print handshake |
| `models/chat.py` | **NEW** — `Chat`, `Message` |
| `models/setting.py` | **NEW** — `Setting` key/value |
| `routers/chats.py` | **NEW** — chat threads + messages |
| `routers/settings.py` | **NEW** — provider selection |
| `routers/credits.py` | **DELETED** |
| `services/extract.py` | **NEW** — `TextExtractor` lifted out of `generator.py` |
| `services/llm/{base,ollama,groq,factory}.py` | **NEW** — replaces `llm.py` |
| `services/knowledge/{base,duckduckgo,none,factory}.py` | **NEW** — replaces `search.py` |
| `services/images/{base,placeholder,factory}.py` | **NEW** — replaces `images.py` (Pollinations gone) |
| `services/generator.py` | **MODIFIED** — call factories, import `TextExtractor` |

### Frontend — `src/` (ported from `frontend/`)

| File | Responsibility |
| --- | --- |
| `main.tsx`, `App.tsx` | Entry + routing |
| `lib/engine.ts` | **NEW** — `invoke("engine_info")`, build base URL + auth header |
| `lib/api.ts` | Ported — same calls, dynamic base URL + token |
| `lib/types.ts` | Ported (credits removed, chat types added) |
| `views/chat/` | **NEW** — ChatGPT-style surface |
| `views/library/` | Ported from `library-client.tsx` |
| `views/reader/` | Ported from `reader-client.tsx` — **typewriter logic preserved verbatim** |
| `components/` | Ported: book-card, book-grid, sidebar, topbar, home-screen |
| `styles/globals.css` | Ported |

---

## Task 1: Verify the toolchain

Nothing else works until this passes. Rust and MSVC are **not installed** on the owner's machine.

**Files:** none (environment only)

- [ ] **Step 1: Check what's already present**

Run:
```bash
node --version && npm --version && ollama --version
```
Expected: `v20.19.2`, `10.8.2`, `ollama version is 0.32.0`. All three already pass.

- [ ] **Step 2: Check Rust (expected to FAIL initially)**

Run:
```bash
rustc --version && cargo --version
```
Expected right now: `command not found`. That is the signal to install.

- [ ] **Step 3: Install Rust**

Download `rustup-init.exe` from https://rustup.rs, run it, press Enter to accept defaults.
**Then close and reopen the terminal** — PATH does not refresh in already-open terminals. This is the #1 cause of "I installed it but it says not found".

- [ ] **Step 4: Install MSVC C++ Build Tools**

Rust on Windows needs Microsoft's C++ linker. Download "Build Tools for Visual Studio" from
https://visualstudio.microsoft.com/visual-cpp-build-tools/ and tick the **"Desktop development with C++"** workload (~2–4 GB).

Without this, `cargo build` later fails with `link.exe not found` — a confusing error that has nothing to do with your code.

- [ ] **Step 5: Verify Rust now works**

Run:
```bash
rustc --version && cargo --version
```
Expected: version strings like `rustc 1.9x.x` and `cargo 1.9x.x`.

- [ ] **Step 6: Record the target triple — you need it for the sidecar filename**

Run:
```bash
rustc --print host-tuple
```
Expected on this machine: `x86_64-pc-windows-msvc`

Write it down. In Task 17 the frozen Python binary **must** be named `pageforge-engine-x86_64-pc-windows-msvc.exe`. A missing or wrong suffix is the most common Tauri sidecar failure.

- [ ] **Step 7: Verify the Python engine still runs today**

Run:
```bash
cd backend && venv/Scripts/python.exe -c "import fastapi, uvicorn, sqlmodel; print('engine deps OK')"
```
Expected: `engine deps OK`

- [ ] **Checkpoint:** nothing to commit. Confirm all six tools report versions before continuing.

---

## Task 2: Engine bootstrap — handshake + stdin watchdog

This is the contract between Rust and Python. Python picks its own port and secret, announces them on stdout, and kills itself if the parent dies.

**Files:**
- Create: `backend/app/engine.py`
- Create: `backend/tests/test_engine.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_engine.py`:
```python
import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_engine_prints_handshake_line():
    """The engine must print exactly one JSON line with ready/port/token."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.engine"],
        cwd=BACKEND,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        line = proc.stdout.readline()
        data = json.loads(line)
        assert data["ready"] is True
        assert isinstance(data["port"], int) and 1024 < data["port"] < 65536
        assert isinstance(data["token"], str) and len(data["token"]) >= 32
    finally:
        proc.kill()
        proc.wait(timeout=10)
```

- [ ] **Step 2: Run it to confirm it fails**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_engine.py -v
```
Expected: FAIL — `No module named app.engine`

- [ ] **Step 3: Write the engine bootstrap**

Create `backend/app/engine.py`:
```python
"""Engine bootstrap.

Picks a free loopback port, mints an auth token, then runs uvicorn.
The handshake line is printed by main.py's lifespan once the app is up.
Exits automatically if the parent process (the Tauri shell) goes away.
"""
import os
import secrets
import socket
import sys
import threading

import uvicorn


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _exit_when_parent_dies() -> None:
    """Blocks until stdin closes, which happens when the parent process exits."""
    for _ in sys.stdin:
        pass
    os._exit(0)


def main() -> None:
    port = _free_port()
    os.environ["ENGINE_PORT"] = str(port)
    os.environ["ENGINE_TOKEN"] = secrets.token_urlsafe(32)
    if len(sys.argv) > 1:
        os.environ["ENGINE_DB_DIR"] = sys.argv[1]

    threading.Thread(target=_exit_when_parent_dies, daemon=True).start()

    from .main import app  # imported after env vars are set

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Print the handshake from the app lifespan**

The lifespan runs *after* uvicorn has bound the socket, so announcing there guarantees the port is actually accepting connections — no race where Rust connects too early.

In `backend/app/main.py`, replace the `lifespan` function with:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    print(json.dumps({
        "ready": True,
        "port": int(os.environ["ENGINE_PORT"]),
        "token": os.environ["ENGINE_TOKEN"],
    }), flush=True)
    yield
```
Add `import json` to the top of `main.py` (`os` is already imported).

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_engine.py -v
```
Expected: PASS

- [ ] **Checkpoint:** commit `backend/app/engine.py`, `backend/app/main.py`, `backend/tests/test_engine.py`.

---

## Task 2b: Stop the test suite generating real books

**Discovered during execution, not planned.** Every later task's "run pytest, expect all pass" step depends on this.

`conftest.py`'s `book_factory` calls `POST /api/books/`, which schedules `run_generation` as a `BackgroundTask`. **TestClient runs background tasks synchronously**, so each test that created a book kicked off a *real* generation — live DuckDuckGo scraping and real LLM calls. The suite hung indefinitely and burned API quota. This is pre-existing, not introduced by Task 2.

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Stub the pipeline for all tests**

Add to `backend/tests/conftest.py`, above `session_fixture`:
```python
@pytest.fixture(autouse=True)
def no_real_generation(monkeypatch):
    """Stop tests from generating real books.

    POST /api/books schedules run_generation as a BackgroundTask, and TestClient
    runs background tasks synchronously — so without this every test that creates
    a book would hit the real LLM and the live web, hanging the suite.
    The pipeline itself is covered directly in test_generator_events.py.
    """
    monkeypatch.setattr("app.routers.books.run_generation", lambda *a, **k: None)
```
`autouse=True` applies it to every test. It patches the name **as imported into `books.py`** (`app.routers.books.run_generation`), not where it is defined — patching `app.services.generator.run_generation` would not work, because `books.py` already holds its own reference.

- [ ] **Step 2: Verify the suite is fast and green**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/ -q
```
Expected: `19 passed` in **under 5 seconds**. If it hangs, the monkeypatch target is wrong.

- [ ] **Checkpoint:** commit `backend/tests/conftest.py`.

---

## Task 3: Bearer-token auth

The engine listens on loopback, so any other program on the machine could drive it. The token stops that.

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/tests/test_auth.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/routers/books.py` (WebSocket token check)
- Modify: `backend/tests/conftest.py` — **unavoidable.** The middleware is global, so the 18 existing `test_books.py` tests go 401 the moment it registers. `client_fixture` must send a token.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_auth.py`. It defines its own **unauthenticated** client (these tests supply their own headers) with an isolated in-memory DB — without the `get_session` override it would read the developer's real `ebooks.db` and fail on a clean checkout:
```python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app


@pytest.fixture
def client(monkeypatch):
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
```

- [ ] **Step 2: Run it to confirm it fails**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_auth.py -v
```
Expected: FAIL — the first two return 200 because no auth exists yet.

- [ ] **Step 3: Write the middleware**

Create `backend/app/auth.py`:
```python
"""Bearer-token auth for the loopback engine.

Only the Tauri shell knows the token (it read it from the handshake), so other
local processes cannot drive the engine.
"""
import os

from fastapi import Request
from fastapi.responses import JSONResponse

PUBLIC_PREFIXES = ("/static",)


async def token_middleware(request: Request, call_next):
    if request.url.path.startswith(PUBLIC_PREFIXES):
        return await call_next(request)

    expected = os.environ.get("ENGINE_TOKEN", "")
    if request.headers.get("authorization") != f"Bearer {expected}":
        return JSONResponse({"detail": "unauthorized"}, status_code=401)

    return await call_next(request)


def ws_token_ok(token: str | None) -> bool:
    """Browsers cannot set WebSocket headers, so the token arrives as a query param."""
    return bool(token) and token == os.environ.get("ENGINE_TOKEN", "")
```

- [ ] **Step 4: Register the middleware and lock down CORS**

In `backend/app/main.py`, replace the CORS block with:
```python
from .auth import token_middleware

# The Tauri WebView origin differs per OS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://tauri.localhost", "tauri://localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(token_middleware)
```
Delete the `_origins = os.getenv("CORS_ORIGINS", ...)` line — the wildcard web-era config is gone.

- [ ] **Step 5: Run the test to verify it passes**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_auth.py -v
```
Expected: 3 passed

- [ ] **Step 6: Protect the WebSocket**

In `backend/app/routers/books.py`, at the very top of `book_ws`, before `await websocket.accept()`:
```python
from ..auth import ws_token_ok

@router.websocket("/{book_id}/ws")
async def book_ws(book_id: int, websocket: WebSocket, session: Session = Depends(get_session)):
    if not ws_token_ok(websocket.query_params.get("token")):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    # ... rest unchanged
```

- [ ] **Step 7: Keep the existing 18 tests passing**

Registering the middleware turns every existing `test_books.py` request into a 401. Update `client_fixture` in `backend/tests/conftest.py` to send a token by default:
```python
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
```
`monkeypatch.setenv` tears the env var down per-test, so it cannot leak into `test_auth.py`, which sets its own token.

Run the **full** suite:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/ -q
```
Expected: `22 passed` in under 5 seconds.

- [ ] **Checkpoint:** commit `auth.py`, `main.py`, `routers/books.py`, `tests/test_auth.py`, `tests/conftest.py`.

---

## Task 4a: Build environment gotchas (discovered during execution)

Three things bit during the real build. Fix them before Task 4 or you will hit them too.

- [ ] **Disk: Rust needs ~5 GB free, and caches hide it**

`target/` reaches ~2 GB, and cargo unpacks crates into `~/.cargo/registry`. A full disk surfaces as `no space on device`, then as a bogus `STATUS_ACCESS_VIOLATION` — which looks like a compiler bug and is not.

The real hogs are usually package caches, not your project. Check and purge:
```bash
pip cache purge          # this machine: 18.81 GB reclaimed
npm cache clean --force  # this machine: 4.44 GB reclaimed
df -h /c                 # confirm 5 GB+ free before building
```
These are download archives, not installed packages. Purging them uninstalls nothing; the next install just re-downloads.

- [ ] **Memory: the default dev profile OOMs LLVM**

`cargo`'s default `debuginfo=2` made `rustc` die with `LLVM ERROR: out of memory`. The Rust here is a 4-file process supervisor — a Rust debugger is not worth an OOM. Add to `src-tauri/Cargo.toml`:
```toml
[profile.dev]
debug = 0
incremental = false
```
And build with `cargo build -j 1` if memory is tight — parallel codegen multiplies peak usage.

- [ ] **The scaffold compiles the library three times**

`tauri init` emits `crate-type = ["staticlib", "cdylib", "rlib"]` so iOS/Android hosts can link against it. This project is desktop-only, so two of those are wasted compiles and a much larger `target/`. In `src-tauri/Cargo.toml`:
```toml
[lib]
name = "app_lib"
crate-type = ["rlib"]
```

- [ ] **Checkpoint:** commit `src-tauri/Cargo.toml`.

---

## Task 4: Scaffold the Tauri shell + Vite frontend

**What this does in plain language:** creates a desktop window that loads a React app. No Python yet — just prove the window opens.

**Files:**
- Create: `package.json`, `vite.config.ts`, `index.html`, `tsconfig.json`
- Create: `src/main.tsx`, `src/App.tsx`
- Create: `src-tauri/` (generated)

- [ ] **Step 1: Create the root `package.json`**

```json
{
  "name": "pageforge",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "tauri": "tauri"
  },
  "dependencies": {
    "@phosphor-icons/react": "^2.1.10",
    "@tauri-apps/api": "^2",
    "@tauri-apps/plugin-shell": "^2",
    "motion": "^12.42.2",
    "react": "^19.2.4",
    "react-dom": "^19.2.4"
  },
  "devDependencies": {
    "@tauri-apps/cli": "^2",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "@vitejs/plugin-react": "^4",
    "typescript": "^5",
    "vite": "^6"
  }
}
```

- [ ] **Step 2: Create `vite.config.ts`**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: { port: 1420, strictPort: true },
})
```
Port 1420 is the Tauri convention; `strictPort` makes a conflict fail loudly instead of silently moving ports (which would leave Tauri loading a blank window).

- [ ] **Step 3: Create `index.html` at the repo root**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Pageforge</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Create `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"]
}
```

- [ ] **Step 5: Create a minimal React entry**

`src/main.tsx`:
```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

`src/App.tsx`:
```tsx
export function App() {
  return <h1 style={{ fontFamily: 'system-ui', padding: 40 }}>Pageforge shell OK</h1>
}
```

- [ ] **Step 6: Install dependencies**

Run:
```bash
npm install
```
Expected: `added N packages`.

- [ ] **Step 7: Initialize Tauri**

Run it non-interactively so the answers are reproducible:
```bash
npx tauri init --app-name "Pageforge" --window-title "Pageforge" \
  --frontend-dist "../dist" --dev-url "http://localhost:1420" \
  --before-dev-command "npm run dev" --before-build-command "npm run build" --ci
```
This generates `src-tauri/`.

**Then fix two scaffold defaults:**

1. **The identifier** — it defaults to `com.tauri.dev`, and it becomes the **app-data folder name**, so your database would live in a directory called `tauri.dev`. In `src-tauri/tauri.conf.json`:
   ```json
   "identifier": "com.pageforge.app",
   ```
2. **Window size** — defaults to 800×600, too cramped for the reader's two-column layout:
   ```json
   {
     "title": "Pageforge",
     "width": 1280, "height": 820,
     "minWidth": 900, "minHeight": 640,
     "resizable": true, "fullscreen": false
   }
   ```

Note the scaffold generates a `lib.rs` + `main.rs` split (for mobile support). Keep it: `main.rs` just calls `app_lib::run()`, and all the real logic goes in `lib.rs`.

- [ ] **Step 8: Run the app — expect a long first build**

Run:
```bash
npm run tauri dev
```

⚠️ **The first run takes 5–15 minutes.** The terminal prints `Compiling ...` hundreds of times while Rust builds every dependency once. **This is normal, not a hang.** Every later run takes seconds.

Expected: a native desktop window opens showing **"Pageforge shell OK"**.

- [ ] **Checkpoint:** commit the root scaffold and `src-tauri/`. Add `src-tauri/target/`, `dist/`, `node_modules/`, and `src-tauri/binaries/` to `.gitignore`.

---

## Task 5: Rust engine supervisor

**What this does in plain language:** when the app starts, Rust launches Python as a child process, waits for it to print `{"ready":true,"port":…,"token":…}`, remembers those values, and kills Python when the app closes.

**Files:**
- Create: `src-tauri/src/state.rs`, `src-tauri/src/engine.rs`, `src-tauri/src/commands.rs`
- Modify: `src-tauri/src/main.rs`, `src-tauri/Cargo.toml`, `src-tauri/capabilities/default.json`

- [ ] **Step 1: Add Rust dependencies**

Run:
```bash
cd src-tauri && cargo add tauri-plugin-shell serde_json && cargo add serde --features derive && cargo add tokio --features time
```
Expected: `Adding ...` lines and an updated `Cargo.toml`.

- [ ] **Step 2: Grant shell permissions**

Tauri denies everything by default. Replace `src-tauri/capabilities/default.json` with:
```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Permissions for the Pageforge shell",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "shell:allow-spawn",
    "shell:allow-kill",
    {
      "identifier": "shell:allow-execute",
      "allow": [
        { "name": "backend/venv/Scripts/python.exe", "cmd": "backend/venv/Scripts/python.exe", "args": true, "sidecar": false },
        { "name": "binaries/pageforge-engine", "sidecar": true, "args": true }
      ]
    }
  ]
}
```
If the app later dies with a "not allowed by scope" error, this file is the place to look.

- [ ] **Step 3: Define the shared state**

Create `src-tauri/src/state.rs`:
```rust
use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri_plugin_shell::process::CommandChild;

/// What the UI needs to talk to the Python engine.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EngineInfo {
    pub port: u16,
    pub token: String,
}

/// Held by Tauri for the life of the app.
#[derive(Default)]
pub struct EngineState {
    pub info: Mutex<Option<EngineInfo>>,
    pub child: Mutex<Option<CommandChild>>,
    /// Set when startup failed, so the UI can show a real reason instead of
    /// spinning forever.
    pub error: Mutex<Option<String>>,
}
```

- [ ] **Step 4: Write the spawn + handshake logic**

Create `src-tauri/src/engine.rs`:
```rust
use crate::state::EngineInfo;
use serde::Deserialize;
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;
use tokio::time::{timeout, Duration};

#[derive(Deserialize)]
struct Handshake {
    ready: bool,
    port: u16,
    token: String,
}

/// Starts the Python engine and waits for its handshake line.
///
/// Dev builds run Python straight from backend/venv so Python edits need only an
/// app restart. Release builds run the PyInstaller-frozen sidecar binary.
pub async fn start(app: &AppHandle) -> Result<(EngineInfo, CommandChild), String> {
    let db_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&db_dir).map_err(|e| e.to_string())?;
    let db_arg = db_dir.to_string_lossy().to_string();

    let (mut rx, child) = if cfg!(debug_assertions) {
        app.shell()
            .command("backend/venv/Scripts/python.exe")
            .args(["-m", "app.engine", &db_arg])
            .current_dir("../backend".into())
            .spawn()
            .map_err(|e| format!("failed to start dev engine: {e}"))?
    } else {
        app.shell()
            .sidecar("pageforge-engine")
            .map_err(|e| format!("sidecar not found: {e}"))?
            .args([&db_arg])
            .spawn()
            .map_err(|e| format!("failed to start engine: {e}"))?
    };

    let mut stderr = String::new();
    let wait = async {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes);
                    if let Ok(h) = serde_json::from_str::<Handshake>(line.trim()) {
                        if h.ready {
                            return Ok(EngineInfo { port: h.port, token: h.token });
                        }
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    stderr.push_str(&String::from_utf8_lossy(&bytes));
                }
                CommandEvent::Terminated(_) => {
                    return Err(format!("engine exited before handshake:\n{stderr}"));
                }
                _ => {}
            }
        }
        Err(format!("engine stream closed before handshake:\n{stderr}"))
    };

    match timeout(Duration::from_secs(30), wait).await {
        Ok(result) => result.map(|info| (info, child)),
        Err(_) => Err("engine did not start within 30 seconds".into()),
    }
}
```

- [ ] **Step 5: Expose engine status + restart to the UI**

Three states matter to the UI: still starting, ready, or failed. Without that distinction the UI cannot tell "wait a moment" from "this is broken" — which is how you get an infinite splash screen.

Create `src-tauri/src/commands.rs`:
```rust
use crate::state::{EngineInfo, EngineState};
use serde::Serialize;
use tauri::{AppHandle, Manager};

#[derive(Serialize, Clone)]
pub struct EngineStatus {
    /// "starting" | "ready" | "failed"
    pub state: String,
    pub info: Option<EngineInfo>,
    pub message: Option<String>,
}

/// The UI polls this on boot. Returning "failed" with a real message lets the UI
/// show the reason instead of spinning forever.
#[tauri::command]
pub fn engine_status(app: AppHandle) -> EngineStatus {
    let state = app.state::<EngineState>();

    if let Some(info) = state.info.lock().unwrap().clone() {
        return EngineStatus { state: "ready".into(), info: Some(info), message: None };
    }
    if let Some(message) = state.error.lock().unwrap().clone() {
        return EngineStatus { state: "failed".into(), info: None, message: Some(message) };
    }
    EngineStatus { state: "starting".into(), info: None, message: None }
}

/// Kills any existing engine and starts a fresh one.
///
/// Takes AppHandle rather than State because the mutex guards must be dropped
/// before the `.await` below — a std Mutex guard cannot be held across await.
#[tauri::command]
pub async fn restart_engine(app: AppHandle) -> Result<EngineInfo, String> {
    {
        let state = app.state::<EngineState>();
        let old = state.child.lock().unwrap().take();
        if let Some(child) = old {
            let _ = child.kill();
        }
        *state.info.lock().unwrap() = None;
        *state.error.lock().unwrap() = None;
    } // guards dropped here, before the await

    match crate::engine::start(&app).await {
        Ok((info, child)) => {
            let state = app.state::<EngineState>();
            *state.info.lock().unwrap() = Some(info.clone());
            *state.child.lock().unwrap() = Some(child);
            Ok(info)
        }
        Err(e) => {
            let state = app.state::<EngineState>();
            *state.error.lock().unwrap() = Some(e.clone());
            Err(e)
        }
    }
}
```

- [ ] **Step 6: Wire it together**

Replace `src-tauri/src/main.rs` with:
```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod engine;
mod state;

use state::EngineState;
use tauri::{Manager, RunEvent};

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(EngineState::default())
        .invoke_handler(tauri::generate_handler![
            commands::engine_status,
            commands::restart_engine
        ])
        .setup(|app| {
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let state = handle.state::<EngineState>();
                match engine::start(&handle).await {
                    Ok((info, child)) => {
                        *state.info.lock().unwrap() = Some(info);
                        *state.child.lock().unwrap() = Some(child);
                    }
                    Err(e) => {
                        // Store it so the UI can display the real reason.
                        eprintln!("ENGINE FAILED: {e}");
                        *state.error.lock().unwrap() = Some(e);
                    }
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error building app")
        .run(|handle, event| {
            // Kill the Python child so it never outlives the window.
            if let RunEvent::Exit = event {
                let state = handle.state::<EngineState>();
                if let Some(child) = state.child.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        });
}
```

- [ ] **Step 7: Run and confirm the engine starts**

Run:
```bash
npm run tauri dev
```
Expected: the window opens showing "Pageforge shell OK", and **no** `ENGINE FAILED` line in the terminal.

- [ ] **Step 8: Prove Python actually died with the app**

Close the window, then run:
```bash
tasklist | grep -i python
```
Expected: no leftover `python.exe` from the app. If one lingers, the `RunEvent::Exit` kill is not firing.

- [ ] **Checkpoint:** commit the four Rust files, `Cargo.toml`, and `capabilities/default.json`.

---

## Task 6: Frontend engine bridge — prove end-to-end

**Files:**
- Create: `src/lib/engine.ts`
- Modify: `src/App.tsx`

- [ ] **Step 1: Write the engine bridge**

Create `src/lib/engine.ts`:
```ts
import { invoke } from '@tauri-apps/api/core'

export interface EngineInfo { port: number; token: string }

interface EngineStatus {
  state: 'starting' | 'ready' | 'failed'
  info: EngineInfo | null
  message: string | null
}

let cached: EngineInfo | null = null

export async function engineStatus(): Promise<EngineStatus> {
  return invoke<EngineStatus>('engine_status')
}

export async function restartEngine(): Promise<EngineInfo> {
  cached = null
  const info = await invoke<EngineInfo>('restart_engine')
  cached = info
  return info
}

/** Waits for the engine, but fails fast with a real reason if it broke. */
export async function getEngine(): Promise<EngineInfo> {
  if (cached) return cached
  for (let attempt = 0; attempt < 60; attempt++) {
    const status = await engineStatus()
    if (status.state === 'ready' && status.info) {
      cached = status.info
      return cached
    }
    if (status.state === 'failed') {
      throw new Error(status.message ?? 'The engine failed to start.')
    }
    await new Promise(r => setTimeout(r, 500))
  }
  throw new Error('The engine did not start within 30 seconds.')
}

export async function apiBase(): Promise<string> {
  const { port } = await getEngine()
  return `http://127.0.0.1:${port}/api`
}

export async function wsBase(): Promise<string> {
  const { port } = await getEngine()
  return `ws://127.0.0.1:${port}/api`
}

export async function authHeaders(): Promise<Record<string, string>> {
  const { token } = await getEngine()
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
}
```

- [ ] **Step 2: Build the EngineGate**

This component owns "is the engine up?" for the whole app. Task 16 wraps the router in it, so the failure/restart UI survives that rewrite.

Create `src/components/engine-gate/engine-gate.tsx`:
```tsx
import { useCallback, useEffect, useState } from 'react'
import { getEngine, restartEngine } from '@/lib/engine'
import s from './engine-gate.module.css'

type Phase = 'starting' | 'ready' | 'failed'

export function EngineGate({ children }: { children: React.ReactNode }) {
  const [phase, setPhase] = useState<Phase>('starting')
  const [message, setMessage] = useState('')

  const connect = useCallback(async () => {
    setPhase('starting')
    try {
      await getEngine()
      setPhase('ready')
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e))
      setPhase('failed')
    }
  }, [])

  useEffect(() => { connect() }, [connect])

  async function retry() {
    setPhase('starting')
    try {
      await restartEngine()
      setPhase('ready')
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e))
      setPhase('failed')
    }
  }

  if (phase === 'ready') return <>{children}</>

  return (
    <div className={s.screen}>
      {phase === 'starting' ? (
        <>
          <div className={s.spinner} />
          <div className={s.label}>Starting engine…</div>
        </>
      ) : (
        <>
          <div className={s.title}>The engine stopped</div>
          <pre className={s.detail}>{message}</pre>
          <button className={s.retry} onClick={retry}>Restart engine</button>
        </>
      )}
    </div>
  )
}
```

Create `src/components/engine-gate/engine-gate.module.css`:
```css
.screen { height: 100vh; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 14px; background: var(--bg); padding: 40px; text-align: center; }
.spinner { width: 26px; height: 26px; border: 2px solid var(--border);
  border-top-color: var(--indigo); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.label { font-size: 14px; color: var(--faint); }
.title { font-size: 17px; font-weight: 700; color: var(--ink); letter-spacing: -0.02em; }
.detail { max-width: 560px; max-height: 220px; overflow: auto; text-align: left;
  font-size: 11.5px; line-height: 1.6; color: oklch(0.78 0.14 20);
  background: oklch(0.12 0.03 20); border: 1px solid oklch(0.25 0.08 20);
  border-radius: 10px; padding: 14px; white-space: pre-wrap; }
.retry { padding: 10px 18px; border: none; border-radius: 9px; background: var(--indigo);
  color: #fff; font-size: 13.5px; font-weight: 600; font-family: inherit; cursor: pointer; }
.retry:hover { opacity: 0.9; }
.retry:active { transform: scale(0.97); }
```

- [ ] **Step 3: Call the engine from the UI**

Replace `src/App.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { EngineGate } from './components/engine-gate/engine-gate'
import { apiBase, authHeaders } from './lib/engine'

function Probe() {
  const [status, setStatus] = useState('checking…')

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${await apiBase()}/books/`, { headers: await authHeaders() })
        setStatus(`engine OK — ${(await res.json()).length} books`)
      } catch (e) {
        setStatus(`FAILED: ${e}`)
      }
    })()
  }, [])

  return <h1 style={{ fontFamily: 'system-ui', padding: 40 }}>{status}</h1>
}

export function App() {
  return <EngineGate><Probe /></EngineGate>
}
```

- [ ] **Step 4: Verify the failure path actually works**

Temporarily break the engine to prove the gate is real. Rename `backend/app/engine.py` to `backend/app/engine_.py`, then run `npm run tauri dev`.

Expected: after a moment the window shows **"The engine stopped"** with the Python traceback (`No module named app.engine`) and a **Restart engine** button — *not* an infinite spinner.

Rename the file back, click **Restart engine**, and the app should recover without you closing it.

- [ ] **Step 5: Verify the whole chain**

Run:
```bash
npm run tauri dev
```
Expected: the window shows **"engine OK — N books"**.

That single line proves: Rust spawned Python → Python picked a port and token → Rust read the handshake → the UI got them → an authenticated HTTP call reached FastAPI and came back. **The architecture is now proven.** Everything after this is porting.

- [ ] **Checkpoint:** commit `src/lib/engine.ts` and `src/App.tsx`.

---

## Task 7: Extract the TextExtractor into its own module

Highest-value test target — its state machine is subtle and silently corrupts the live preview when wrong.

**Files:**
- Create: `backend/app/services/extract.py`
- Create: `backend/tests/test_extract.py`
- Modify: `backend/app/services/generator.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_extract.py`:
```python
from app.services.extract import TextExtractor


def collect(chunks: list[str]) -> str:
    out: list[str] = []
    ex = TextExtractor(out.append)
    for c in chunks:
        ex.feed(c)
    return "".join(out)


def test_emits_only_text_field_prose():
    raw = '{"pages":[{"heading":"H","text":"Hello world","page_number":1}]}'
    assert collect([raw]) == "Hello world"


def test_ignores_other_string_fields():
    raw = '{"pages":[{"heading":"Ignore me","text":"Keep me"}]}'
    assert collect([raw]) == "Keep me"


def test_decodes_escape_sequences():
    raw = '{"text":"Line one\\nLine two"}'
    assert collect([raw]) == "Line one\nLine two"


def test_escaped_quote_does_not_end_the_value():
    raw = '{"text":"She said \\"hi\\" loudly"}'
    assert collect([raw]) == 'She said "hi" loudly'


def test_works_when_split_across_token_boundaries():
    """Tokens arrive in arbitrary chunks — the marker can be split in half."""
    assert collect(['{"te', 'xt":"Hel', 'lo"}']) == "Hello"


def test_handles_multiple_text_fields():
    raw = '{"pages":[{"text":"One"},{"text":"Two"}]}'
    assert collect([raw]) == "OneTwo"
```

- [ ] **Step 2: Run to confirm they fail**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_extract.py -v
```
Expected: FAIL — `No module named app.services.extract`

- [ ] **Step 3: Move the class into its own module**

**The shipped class has a real bug: it does not handle `\uXXXX` escapes.** Models emit those constantly for smart quotes, accents and dashes. Proven during execution:

| | Output |
| --- | --- |
| Raw stream | `{"text":"naïve it’s"}` |
| Live preview (old code) | `nau00efve itu2019s` ← garbage |
| Finished book (`json.loads`) | `naïve it’s` ← correct |

The reader watches `itu2019s` type out, then it silently "corrects" to `it’s` when the page saves. The port below fixes it — decoding now matches `json.loads` exactly, including surrogate pairs (emoji).

Create `backend/app/services/extract.py`:
```python
"""Pulls prose out of a streaming JSON response.

The LLM streams raw JSON. The UI only wants the value of each "text" field, so
this walks the stream character by character and emits just that prose.

Decoding must match json.loads() exactly: whatever the reader watches being
typed live has to equal the text that ends up in the finished book. Anything
this gets wrong appears as garbage in the live preview that then silently
"corrects" itself once the page is saved.
"""
from typing import Callable


class TextExtractor:
    # JSON's two-character escapes.
    _ESC = {
        'n': '\n', 't': '\t', 'r': '\r',
        'b': '\b', 'f': '\f',
        '"': '"', '\\': '\\', '/': '/',
    }

    def __init__(self, notify: Callable[[str], None]):
        self._notify = notify
        self._buf = ""
        self._in_value = False
        self._esc = False
        self._uni: str | None = None    # collecting the 4 hex digits after \u
        self._high: int | None = None   # pending high surrogate

    def _emit_code(self, code: int) -> None:
        r"""Emit one \uXXXX escape, joining surrogate pairs (e.g. emoji)."""
        if 0xD800 <= code <= 0xDBFF:        # high surrogate: wait for its partner
            self._high = code
            return
        if self._high is not None:
            high, self._high = self._high, None
            if 0xDC00 <= code <= 0xDFFF:    # valid pair -> one character
                self._notify(chr(0x10000 + ((high - 0xD800) << 10) + (code - 0xDC00)))
                return
            # orphaned high surrogate: drop it rather than emit a lone surrogate
        self._notify(chr(code))

    def feed(self, raw: str) -> None:
        for ch in raw:
            if self._in_value:
                if self._uni is not None:
                    self._uni += ch
                    if len(self._uni) == 4:
                        try:
                            self._emit_code(int(self._uni, 16))
                        except ValueError:
                            pass            # malformed escape: skip it
                        self._uni = None
                elif self._esc:
                    self._esc = False
                    if ch == 'u':
                        self._uni = ""
                    else:
                        self._notify(self._ESC.get(ch, ch))
                elif ch == '\\':
                    self._esc = True
                elif ch == '"':
                    self._in_value = False
                    self._buf = ""
                    self._high = None
                else:
                    self._notify(ch)
            else:
                self._buf += ch
                if self._buf.endswith('"'):
                    tail = self._buf[-20:].replace(' ', '')
                    if tail.endswith('"text":"'):
                        self._in_value = True
                        self._buf = ""
                if len(self._buf) > 60:
                    self._buf = self._buf[-60:]
```

Add these tests to `backend/tests/test_extract.py` (they fail against the old code, proving the bug):
```python
import json

# NOTE: chr(92) builds a REAL backslash. Writing '\\u00ef' in a test would be
# decoded by Python's own literal parser, so the extractor would never see an
# escape — the test would pass while proving nothing.
B = chr(92)


def test_decodes_unicode_escapes():
    raw = '{"text":"na' + B + 'u00efve it' + B + 'u2019s"}'
    assert collect([raw]) == json.loads(raw)["text"] == "naïve it’s"


def test_unicode_escape_split_across_token_boundaries():
    assert collect(['{"text":"a' + B + 'u20', '19b"}']) == "a’b"


def test_decodes_surrogate_pair():
    """Emoji arrive as two escapes that must be combined into one character."""
    raw = '{"text":"hi ' + B + 'ud83d' + B + 'ude00"}'
    assert collect([raw]) == json.loads(raw)["text"] == "hi 😀"


def test_decodes_control_escapes_like_json():
    raw = '{"text":"a' + B + 'tb' + B + '/c"}'
    assert collect([raw]) == json.loads(raw)["text"] == "a\tb/c"
```

- [ ] **Step 4: Run to verify they pass**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_extract.py -v
```
Expected: 6 passed

- [ ] **Step 5: Delete the old copy and import the new one**

In `backend/app/services/generator.py`: delete the entire `class _TextExtractor` block, and add to the imports:
```python
from .extract import TextExtractor
```
Then change the one usage site from `_TextExtractor(...)` to `TextExtractor(...)`.

- [ ] **Step 6: Confirm nothing else broke**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/ -v
```
Expected: all tests pass.

- [ ] **Checkpoint:** commit `extract.py`, `generator.py`, `tests/test_extract.py`.

---

## Task 8: LLM providers

Replaces `llm.py`'s hardcoded Groq/Ollama branch with a swappable provider.

**Files:**
- Create: `backend/app/services/llm/{__init__,base,ollama,groq,factory}.py`
- Delete: `backend/app/services/llm.py`
- Create: `backend/tests/test_llm_factory.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_llm_factory.py`:
```python
import pytest

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
```

- [ ] **Step 2: Run to confirm it fails**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_llm_factory.py -v
```
Expected: FAIL — `No module named app.services.llm.factory`

- [ ] **Step 3: Define the interface**

Create `backend/app/services/llm/__init__.py` (empty file).

Create `backend/app/services/llm/base.py`:
```python
from abc import ABC, abstractmethod
from typing import Callable


class LlmProvider(ABC):
    """Streams a JSON completion, emitting each token as it arrives."""

    @abstractmethod
    def stream_json(self, prompt: str, on_token: Callable[[str], None]) -> dict:
        ...


class LlmUnavailable(RuntimeError):
    """Raised with a message the user can act on."""
```

- [ ] **Step 4: Implement the Ollama provider (the default)**

Create `backend/app/services/llm/ollama.py`:
```python
import json
import os
from typing import Callable

import httpx

from .base import LlmProvider, LlmUnavailable

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class OllamaProvider(LlmProvider):
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1")

    def stream_json(self, prompt: str, on_token: Callable[[str], None]) -> dict:
        body = {"model": self.model, "prompt": prompt, "format": "json", "stream": True}
        full = ""
        try:
            with httpx.stream("POST", f"{OLLAMA_URL}/api/generate", json=body, timeout=600) as r:
                if r.status_code == 404:
                    raise LlmUnavailable(
                        f"Model '{self.model}' not found. Run: ollama pull {self.model}"
                    )
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        full += token
                        on_token(token)
        except httpx.ConnectError as e:
            raise LlmUnavailable("Ollama isn't running — start it and try again.") from e
        return json.loads(full)
```

- [ ] **Step 5: Implement the Groq provider (opt-in)**

Create `backend/app/services/llm/groq.py`:
```python
import json
import os
from typing import Callable

from groq import Groq

from .base import LlmProvider, LlmUnavailable


class GroqProvider(LlmProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def stream_json(self, prompt: str, on_token: Callable[[str], None]) -> dict:
        if not self.api_key:
            raise LlmUnavailable("No Groq API key set. Add one in Settings, or switch to Ollama.")
        stream = Groq(api_key=self.api_key).chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
            stream=True,
        )
        full = ""
        for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            if token:
                full += token
                on_token(token)
        return json.loads(full)
```

- [ ] **Step 6: Write the factory**

Create `backend/app/services/llm/factory.py`:
```python
from .base import LlmProvider
from .groq import GroqProvider
from .ollama import OllamaProvider


def get_llm(name: str = "ollama", **kwargs) -> LlmProvider:
    """Adding a provider = one import + one line here."""
    if name == "ollama":
        return OllamaProvider(**kwargs)
    if name == "groq":
        return GroqProvider(**kwargs)
    raise ValueError(f"unknown llm provider: {name}")
```

- [ ] **Step 7: Run to verify it passes**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_llm_factory.py -v
```
Expected: 3 passed

- [ ] **Step 8: Add the bad-JSON retry**

LLMs occasionally emit malformed JSON. One retry fixes most of it, and a whole book should never die because of a single stray token.

Add to `backend/tests/test_llm_factory.py`:
```python
import json

from app.services.llm.base import LlmProvider, stream_json_with_retry


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
```

Then append to `backend/app/services/llm/base.py`:
```python
import json
from typing import Callable


def stream_json_with_retry(
    provider: "LlmProvider",
    prompt: str,
    on_token: Callable[[str], None],
    attempts: int = 2,
) -> dict:
    """Retries once when the model emits malformed JSON.

    Lives here rather than in each provider so every provider gets it for free.
    """
    for attempt in range(attempts):
        try:
            return provider.stream_json(prompt, on_token)
        except json.JSONDecodeError:
            if attempt == attempts - 1:
                raise
    raise AssertionError("unreachable")
```

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_llm_factory.py -v
```
Expected: 5 passed

- [ ] **Step 9: Delete the old module**

Delete `backend/app/services/llm.py`. `generator.py` still imports from it and will be fixed in Task 11.

- [ ] **Checkpoint:** commit the `llm/` package, the deletion, and the test.

---

## Task 9: Knowledge providers

**Files:**
- Create: `backend/app/services/knowledge/{__init__,base,duckduckgo,none,factory}.py`
- Delete: `backend/app/services/search.py`
- Create: `backend/tests/test_knowledge.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_knowledge.py`:
```python
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
```

- [ ] **Step 2: Run to confirm it fails**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_knowledge.py -v
```
Expected: FAIL — module not found

- [ ] **Step 3: Define the interface**

Create `backend/app/services/knowledge/__init__.py` (empty).

Create `backend/app/services/knowledge/base.py`:
```python
from abc import ABC, abstractmethod

NO_RESEARCH = "No research data available."


class KnowledgeProvider(ABC):
    """Returns (facts_for_the_prompt, sources_to_cite)."""

    @abstractmethod
    def research(self, topic: str) -> tuple[str, list[dict]]:
        ...
```

- [ ] **Step 4: Implement the no-op provider**

Create `backend/app/services/knowledge/none.py`:
```python
from .base import NO_RESEARCH, KnowledgeProvider


class NoneProvider(KnowledgeProvider):
    def research(self, topic: str) -> tuple[str, list[dict]]:
        return NO_RESEARCH, []
```

- [ ] **Step 5: Move DuckDuckGo behind the interface**

Create `backend/app/services/knowledge/duckduckgo.py`:
```python
from duckduckgo_search import DDGS

from .base import NO_RESEARCH, KnowledgeProvider


class DuckDuckGoProvider(KnowledgeProvider):
    """Temporary default. Replaced by ZimProvider in Phase 3."""

    def _search(self, query: str, max_results: int) -> list[dict]:
        return list(DDGS().text(query, max_results=max_results))

    def research(self, topic: str) -> tuple[str, list[dict]]:
        queries = [
            (topic, 4),
            (f"{topic} site:wikipedia.org", 2),
            (f"{topic} facts history key information", 2),
        ]
        seen: set[str] = set()
        results: list[dict] = []

        for query, limit in queries:
            try:
                hits = self._search(query, limit)
            except Exception:
                continue  # never let a flaky scraper kill a book
            for r in hits:
                url = r.get("href", "")
                if url and url not in seen:
                    seen.add(url)
                    results.append(r)

        if not results:
            return NO_RESEARCH, []

        text = "\n".join(f"- {r['title']}: {r['body']}" for r in results)
        sources = [{"title": r["title"], "url": r["href"]} for r in results if r.get("href")]
        return text, sources
```

- [ ] **Step 6: Write the factory**

Create `backend/app/services/knowledge/factory.py`:
```python
from .base import KnowledgeProvider
from .duckduckgo import DuckDuckGoProvider
from .none import NoneProvider


def get_knowledge(name: str = "duckduckgo") -> KnowledgeProvider:
    """Phase 3 adds: if name == "zim": return ZimProvider()"""
    if name == "duckduckgo":
        return DuckDuckGoProvider()
    if name == "none":
        return NoneProvider()
    raise ValueError(f"unknown knowledge provider: {name}")
```

- [ ] **Step 7: Run to verify it passes**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_knowledge.py -v
```
Expected: 3 passed

- [ ] **Step 8: Delete the old module**

Delete `backend/app/services/search.py`.

- [ ] **Checkpoint:** commit the `knowledge/` package, the deletion, and the test.

---

## Task 10: Image providers — remove Pollinations

**Files:**
- Create: `backend/app/services/images/{__init__,base,placeholder,factory}.py`
- Delete: `backend/app/services/images.py`
- Create: `backend/tests/test_images.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_images.py`:
```python
from app.services.images.factory import get_images
from app.services.images.placeholder import PlaceholderProvider


def test_factory_returns_placeholder():
    assert isinstance(get_images("placeholder"), PlaceholderProvider)


def test_placeholder_generates_no_image_but_does_not_fail():
    assert PlaceholderProvider().generate("a castle at dusk", 1, 1) is None
```

- [ ] **Step 2: Run to confirm it fails**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_images.py -v
```
Expected: FAIL — module not found

- [ ] **Step 3: Define the interface**

Create `backend/app/services/images/__init__.py` (empty).

Create `backend/app/services/images/base.py`:
```python
from abc import ABC, abstractmethod

REAL_PERSON_MESSAGE = (
    "Real person image required. "
    "Please provide a licensed image or add it manually."
)


class ImageProvider(ABC):
    """Returns a served URL for the page image, or None if none was produced."""

    @abstractmethod
    def generate(self, prompt: str, book_id: int, page: int) -> str | None:
        ...
```

- [ ] **Step 4: Implement the placeholder provider**

Create `backend/app/services/images/placeholder.py`:
```python
from .base import ImageProvider


class PlaceholderProvider(ImageProvider):
    """Phase 1 default: prompts are generated and stored, but no image is rendered.

    FLUX.1 Schnell / Z Image Turbo will slot in here as a sibling class.
    """

    def generate(self, prompt: str, book_id: int, page: int) -> str | None:
        return None
```

- [ ] **Step 5: Write the factory**

Create `backend/app/services/images/factory.py`:
```python
from .base import ImageProvider
from .placeholder import PlaceholderProvider


def get_images(name: str = "placeholder") -> ImageProvider:
    """Later: if name == "flux": return FluxProvider()"""
    if name == "placeholder":
        return PlaceholderProvider()
    raise ValueError(f"unknown image provider: {name}")
```

- [ ] **Step 6: Run to verify it passes**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_images.py -v
```
Expected: 2 passed

- [ ] **Step 7: Delete Pollinations**

Delete `backend/app/services/images.py`. The rate-limit retry logic goes with it — it was cloud-only and is no longer wanted.

- [ ] **Checkpoint:** commit the `images/` package, the deletion, and the test.

---

## Task 11: Wire the generator to the factories

**Files:**
- Modify: `backend/app/services/generator.py`
- Create: `backend/tests/test_generator_events.py`

- [ ] **Step 1: Write the failing test**

This is the test the old architecture could not have. Create `backend/tests/test_generator_events.py`:
```python
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
```

- [ ] **Step 2: Run to confirm it fails**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_generator_events.py -v
```
Expected: FAIL — `generator` still imports the deleted `llm`/`search`/`images` modules.

- [ ] **Step 3: Swap the imports**

At the top of `backend/app/services/generator.py`, replace the old service imports with:
```python
from .extract import TextExtractor
from .images.base import REAL_PERSON_MESSAGE
from .images.factory import get_images
from .knowledge.factory import get_knowledge
from .llm.base import stream_json_with_retry
from .llm.factory import get_llm
```

- [ ] **Step 4: Resolve providers once at the top of `_generate`**

Immediately after `def _generate(book, session, notify):`, insert:
```python
    llm = get_llm(os.getenv("LLM_PROVIDER", "ollama"))
    knowledge = get_knowledge(os.getenv("KNOWLEDGE_PROVIDER", "duckduckgo"))
    images = get_images(os.getenv("IMAGE_PROVIDER", "placeholder"))
```
Add `import os` at the top of the file if it is not already present.

- [ ] **Step 5: Replace the three call sites**

- Research: `facts, sources = research(...)` → `facts, sources = knowledge.research(f"{book.title} {book.prompt}")`
- Blueprint: `blueprint = generate_json(...)` → `blueprint = stream_json_with_retry(llm, _BLUEPRINT_PROMPT.format(...), lambda _t: None)`
  (the blueprint is not shown to the user, so its tokens are discarded)
- Chapter: `chapter_data = stream_json(..., extractor.feed)` → `chapter_data = stream_json_with_retry(llm, _CHAPTER_PROMPT.format(...), extractor.feed)`
- Image: `img_url = download_image(img_prompt, "", book.id, ...)` → `img_url = images.generate(img_prompt, book.id, p.get("page_number", i + 1))`

Both LLM calls go through `stream_json_with_retry`, so a single malformed response never kills a book.

- [ ] **Step 6: Run to verify it passes**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/ -v
```
Expected: all tests pass.

- [ ] **Checkpoint:** commit `generator.py` and `tests/test_generator_events.py`.

---

## Task 12: Chat + Settings models and routers

**Files:**
- Create: `backend/app/models/chat.py`, `backend/app/models/setting.py`
- Create: `backend/app/routers/chats.py`, `backend/app/routers/settings.py`
- Create: `backend/tests/test_chats.py`
- Modify: `backend/app/main.py`, `backend/app/database.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_chats.py`:
```python
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ENGINE_PORT", "12345")
    monkeypatch.setenv("ENGINE_TOKEN", "t")
    from app.main import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer t"}


def test_create_and_list_chat(client):
    created = client.post("/api/chats/", json={"title": "Ancient Rome"}, headers=AUTH)
    assert created.status_code == 201
    assert created.json()["title"] == "Ancient Rome"

    listed = client.get("/api/chats/", headers=AUTH)
    assert listed.status_code == 200
    assert any(c["title"] == "Ancient Rome" for c in listed.json())


def test_append_and_read_messages(client):
    chat_id = client.post("/api/chats/", json={"title": "T"}, headers=AUTH).json()["id"]
    client.post(f"/api/chats/{chat_id}/messages",
                json={"role": "user", "content": "Write a book"}, headers=AUTH)
    msgs = client.get(f"/api/chats/{chat_id}/messages", headers=AUTH).json()
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Write a book"
```

- [ ] **Step 2: Run to confirm it fails**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/test_chats.py -v
```
Expected: FAIL — 404, the routes do not exist.

- [ ] **Step 3: Add the models**

Create `backend/app/models/chat.py`:
```python
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Chat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(foreign_key="chat.id", index=True)
    role: str                       # 'user' | 'assistant'
    content: str
    book_id: Optional[int] = Field(default=None, foreign_key="book.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

Create `backend/app/models/setting.py`:
```python
from sqlmodel import Field, SQLModel


class Setting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str
```

- [ ] **Step 4: Register the models so tables get created**

In `backend/app/database.py`, import them above `create_db` so SQLModel sees them:
```python
from .models.book import Book        # noqa: F401
from .models.chat import Chat, Message   # noqa: F401
from .models.setting import Setting      # noqa: F401
```

- [ ] **Step 5: Add the chats router**

Create `backend/app/routers/chats.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models.chat import Chat, Message

router = APIRouter()


@router.post("/", response_model=Chat, status_code=201)
def create_chat(data: dict, session: Session = Depends(get_session)):
    chat = Chat(title=data.get("title", "New chat"))
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


@router.get("/", response_model=list[Chat])
def list_chats(session: Session = Depends(get_session)):
    return session.exec(select(Chat).order_by(Chat.created_at.desc())).all()


@router.delete("/{chat_id}", status_code=204)
def delete_chat(chat_id: int, session: Session = Depends(get_session)):
    chat = session.get(Chat, chat_id)
    if not chat:
        raise HTTPException(404, "chat not found")
    for m in session.exec(select(Message).where(Message.chat_id == chat_id)).all():
        session.delete(m)
    session.delete(chat)
    session.commit()


@router.post("/{chat_id}/messages", response_model=Message, status_code=201)
def add_message(chat_id: int, data: dict, session: Session = Depends(get_session)):
    if not session.get(Chat, chat_id):
        raise HTTPException(404, "chat not found")
    msg = Message(
        chat_id=chat_id,
        role=data["role"],
        content=data["content"],
        book_id=data.get("book_id"),
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg


@router.get("/{chat_id}/messages", response_model=list[Message])
def list_messages(chat_id: int, session: Session = Depends(get_session)):
    return session.exec(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
    ).all()
```

- [ ] **Step 6: Add the settings router**

Create `backend/app/routers/settings.py`:
```python
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models.setting import Setting

router = APIRouter()

DEFAULTS = {
    "llm_provider": "ollama",
    "ollama_model": "llama3.1",
    "groq_api_key": "",
    "knowledge_provider": "duckduckgo",
    "image_provider": "placeholder",
}


@router.get("/")
def get_settings(session: Session = Depends(get_session)) -> dict:
    stored = {s.key: s.value for s in session.exec(select(Setting)).all()}
    return {**DEFAULTS, **stored}


@router.put("/")
def update_settings(data: dict, session: Session = Depends(get_session)) -> dict:
    for key, value in data.items():
        if key not in DEFAULTS:
            continue
        row = session.get(Setting, key)
        if row:
            row.value = str(value)
        else:
            session.add(Setting(key=key, value=str(value)))
    session.commit()
    return get_settings(session)
```

- [ ] **Step 7: Register the routers and drop credits**

In `backend/app/main.py`:
```python
from .routers import books, chats, settings

app.include_router(books.router,    prefix="/api/books",    tags=["books"])
app.include_router(chats.router,    prefix="/api/chats",    tags=["chats"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
```
Remove the `credits` import and its `include_router` line, then delete `backend/app/routers/credits.py`.

- [ ] **Step 8: Run to verify it passes**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/ -v
```
Expected: all tests pass.

- [ ] **Checkpoint:** commit the models, routers, `main.py`, `database.py`, the credits deletion, and the test.

---

## Task 13: Store the database in the OS app-data directory

Today the DB lands in the current working directory. An installed app must not write next to its executable.

**Files:**
- Modify: `backend/app/database.py`

- [ ] **Step 1: Use the directory Rust passes in**

In `backend/app/database.py`, replace the `DATABASE_URL` line with:
```python
import os
from pathlib import Path

_db_dir = os.getenv("ENGINE_DB_DIR")
if _db_dir:
    Path(_db_dir).mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{Path(_db_dir) / 'pageforge.db'}"
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ebooks.db")
```
Rust passes `ENGINE_DB_DIR` as `argv[1]` (Task 5); `engine.py` puts it in the environment (Task 2). The fallback keeps `pytest` working outside the shell.

- [ ] **Step 2: Verify tests still pass**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/ -v
```
Expected: all tests pass.

- [ ] **Step 3: Verify the real DB path in the app**

Run `npm run tauri dev`, generate nothing, then check:
```bash
ls "$APPDATA/com.pageforge.app/"
```
Expected: `pageforge.db` exists there (the exact folder matches the `identifier` in `tauri.conf.json`).

- [ ] **Checkpoint:** commit `database.py`.

---

## Task 14: Port shared components and styles

**Files:**
- Create: `src/styles/globals.css`, `src/lib/types.ts`, `src/lib/api.ts`
- Create: `src/components/{book-card,book-grid,sidebar,topbar}/`

- [ ] **Step 1: Copy the files that need no changes**

Copy these verbatim from `frontend/` to `src/`:
```
frontend/styles/globals.css              → src/styles/globals.css
frontend/components/book-card/*          → src/components/book-card/
frontend/components/book-grid/*          → src/components/book-grid/
frontend/components/topbar/*             → src/components/topbar/
frontend/components/sidebar/*            → src/components/sidebar/
```
CSS Modules, `motion`, and `@phosphor-icons/react` all work identically under Vite — no changes needed.

- [ ] **Step 2: Import the global stylesheet, and drop the Next.js font variable**

Add to the top of `src/main.tsx`:
```tsx
import './styles/globals.css'
```

`globals.css` references `var(--font-geist-sans)`, which was injected by Next.js's font loader. That loader doesn't exist here, so the variable resolves to nothing and body text silently falls back to a serif. Replace every occurrence:
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
```
Verify none remain: `grep -n "font-geist" src/styles/globals.css` → no results.

- [ ] **Step 2b: Declare CSS Modules for TypeScript**

Next.js shipped these types automatically; Vite does not, so every `import s from './x.module.css'` fails to typecheck. Create `src/vite-env.d.ts`:
```ts
/// <reference types="vite/client" />

// Next.js generated these automatically; Vite needs them declared.
declare module '*.module.css' {
  const classes: { readonly [key: string]: string }
  export default classes
}
```

- [ ] **Step 3: Port the types, dropping credits and adding chat**

Create `src/lib/types.ts` by copying `frontend/lib/types.ts`, then **delete the `Credits` interface** and append:
```ts
export interface Chat {
  id: number
  title: string
  created_at: string
}

export interface Message {
  id: number
  chat_id: number
  role: 'user' | 'assistant'
  content: string
  book_id: number | null
  created_at: string
}
```

- [ ] **Step 4: Port the API client onto the engine bridge**

Create `src/lib/api.ts`:
```ts
import { apiBase, authHeaders } from './engine'
import type { Book, BookCreate, Chat, Message } from './types'

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${await apiBase()}${path}`, {
    ...init,
    headers: { ...(await authHeaders()), ...(init.headers ?? {}) },
  })
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.status === 204 ? (undefined as T) : res.json()
}

export const api = {
  books: {
    list:   () => req<Book[]>('/books/'),
    get:    (id: number) => req<Book>(`/books/${id}`),
    create: (data: BookCreate & { cover_hue: number }) =>
      req<Book>('/books/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: number, data: Partial<Book>) =>
      req<Book>(`/books/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: number) => req<void>(`/books/${id}`, { method: 'DELETE' }),
  },
  chats: {
    list:     () => req<Chat[]>('/chats/'),
    create:   (title: string) =>
      req<Chat>('/chats/', { method: 'POST', body: JSON.stringify({ title }) }),
    delete:   (id: number) => req<void>(`/chats/${id}`, { method: 'DELETE' }),
    messages: (id: number) => req<Message[]>(`/chats/${id}/messages`),
    addMessage: (id: number, role: string, content: string, book_id?: number) =>
      req<Message>(`/chats/${id}/messages`, {
        method: 'POST',
        body: JSON.stringify({ role, content, book_id }),
      }),
  },
}
```

- [ ] **Step 5: Remove the credits meter from the sidebar**

In `src/components/sidebar/sidebar.tsx`: delete the `credits` prop from `Props`, delete the `pct` calculation, and delete the entire `<div className={s.footer}>…</div>` block. Then remove the now-unused `.creditsBox`, `.creditsRow`, `.creditsLabel`, `.creditsValue`, `.creditsTrack`, `.creditsBar`, and `.buyLink` rules from `sidebar.module.css`.

- [ ] **Step 6: Verify it compiles**

Run:
```bash
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Checkpoint:** commit `src/components/`, `src/lib/`, `src/styles/`.

---

## Task 15: Port the Library and Reader views

The Reader's typewriter pacing was tuned by hand. **Preserve it verbatim** — only the WebSocket URL changes.

**Files:**
- Create: `src/views/library/`, `src/views/reader/`

- [ ] **Step 1: Copy the view files**

```
frontend/app/(app)/library/library-client.tsx      → src/views/library/library.tsx
frontend/app/(app)/library/library.module.css      → src/views/library/library.module.css
frontend/app/(app)/library/[id]/reader-client.tsx  → src/views/reader/reader.tsx
frontend/app/(app)/library/[id]/reader.module.css  → src/views/reader/reader.module.css
```

- [ ] **Step 2: Replace Next.js routing in the Library**

In `src/views/library/library.tsx`:
- Delete `import { useRouter } from 'next/navigation'` and the `'use client'` line.
- Change the component signature to accept navigation as a prop:
```tsx
interface Props { onOpenBook: (id: number) => void }

export function LibraryView({ onOpenBook }: Props) {
```
- Delete `const router = useRouter()`.
- Replace `handleRead` with:
```tsx
  function handleRead(id: number) {
    onOpenBook(id)
  }
```
- Delete the `credits` state, the `api.credits.get()` call in the mount effect, the `api.credits.consume()` call in `handleCreate`, and the `credits={credits}` prop passed to `<Sidebar>`.

- [ ] **Step 3: Point the Library's WebSocket at the engine**

In `src/views/library/library.tsx`, replace the WebSocket effect's URL construction:
```tsx
  useEffect(() => {
    const generating = books.filter(b => b.status === 'generating')
    if (!generating.length) return

    let cancelled = false
    ;(async () => {
      const { wsBase } = await import('@/lib/engine')
      const { getEngine } = await import('@/lib/engine')
      const base = await wsBase()
      const { token } = await getEngine()
      if (cancelled) return

      generating.forEach(book => {
        if (wsRefs.current[book.id]) return
        const ws = new WebSocket(`${base}/books/${book.id}/ws?token=${token}`)
        wsRefs.current[book.id] = ws
        // ...the existing ws.onmessage / onerror / onclose handlers are unchanged
      })
    })()

    return () => { cancelled = true }
  }, [books])
```
Everything inside `ws.onmessage` stays exactly as it is.

- [ ] **Step 4: Port the Reader — change ONLY the URL**

In `src/views/reader/reader.tsx`:
- Delete `'use client'` and `import { useRouter } from 'next/navigation'`.
- Change the signature to `export function ReaderView({ id, onBack }: { id: number; onBack: () => void })`.
- Replace `router.push('/library')` with `onBack()`.
- Replace the WebSocket URL block with:
```tsx
        const { wsBase, getEngine } = await import('@/lib/engine')
        const base = await wsBase()
        const { token } = await getEngine()
        const ws = new WebSocket(`${base}/books/${id}/ws?token=${token}`)
```

**Do not touch** `bufferRef`, `displayText`, the `step = behind > 300 ? 4 : behind > 80 ? 2 : 1` pacing, the `28`ms interval, the auto-scroll effect, `.cursor`, `.imgGen`, or `.imgFade`. That behaviour is signed off.

- [ ] **Step 5: Verify it compiles**

Run:
```bash
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Checkpoint:** commit `src/views/library/` and `src/views/reader/`.

---

## Task 16: The chat view + app routing

**Files:**
- Create: `src/views/chat/chat.tsx`, `src/views/chat/chat.module.css`
- Modify: `src/App.tsx`

- [ ] **Step 1: Build the chat surface**

Create `src/views/chat/chat.tsx`:
```tsx
import { useState } from 'react'
import { BookOpen, PaperPlaneRight } from '@phosphor-icons/react'
import { api } from '@/lib/api'
import type { Book } from '@/lib/types'
import s from './chat.module.css'

const HUE_CYCLE = [264, 155, 340, 40, 200, 290, 175]

const WRITING_STYLES = [
  { value: 'expository',  label: 'Expository'  },
  { value: 'descriptive', label: 'Descriptive' },
  { value: 'narrative',   label: 'Narrative'   },
  { value: 'persuasive',  label: 'Persuasive'  },
] as const

interface Props { onOpenBook: (id: number) => void }

/** Parses "Write a 15 page book about Ancient Rome" → {pages, title}. */
function parsePrompt(text: string): { title: string; pages: number } {
  const pages = Number(text.match(/(\d+)\s*[- ]?page/i)?.[1] ?? 12)
  const title = text.match(/about\s+(.+?)[.?!]*$/i)?.[1]?.trim() || text.slice(0, 60)
  return { title, pages: Math.min(Math.max(pages, 6), 48) }
}

export function ChatView({ onOpenBook }: Props) {
  const [input, setInput] = useState('')
  const [style, setStyle] = useState('')
  const [sending, setSending] = useState(false)
  const [book, setBook] = useState<Book | null>(null)

  async function send(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim() || sending) return
    setSending(true)
    try {
      const { title, pages } = parsePrompt(input)
      const created = await api.books.create({
        title,
        prompt: input,
        book_type: 'guide',
        page_count: pages,
        illustration_style: 'watercolor',
        use_research: true,
        writing_style: style,
        cover_hue: HUE_CYCLE[Math.floor(Math.random() * HUE_CYCLE.length)],
      })
      setBook(created)
      onOpenBook(created.id)   // jump straight into the live reader
    } finally {
      setSending(false)
    }
  }

  return (
    <div className={s.page}>
      <div className={s.center}>
        <div className={s.hero}>
          <div className={s.logoMark}><BookOpen size={20} weight="bold" /></div>
          <h1 className={s.name}>Pageforge</h1>
          <p className={s.tagline}>Describe a book and watch it write itself</p>
        </div>

        <form className={s.form} onSubmit={send}>
          <textarea
            className={s.input}
            placeholder="Write a 15 page book about Ancient Rome"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(e) }
            }}
            rows={3}
            autoFocus
          />

          <div className={s.styleRow}>
            {WRITING_STYLES.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                className={`${s.pill} ${style === value ? s.pillActive : ''}`}
                onClick={() => setStyle(style === value ? '' : value)}
              >
                {label}
              </button>
            ))}
          </div>

          <button className={s.send} type="submit" disabled={!input.trim() || sending}>
            {sending ? 'Starting…' : <><PaperPlaneRight size={15} weight="fill" /> Generate Book</>}
          </button>
        </form>

        {book && (
          <button className={s.resultCard} onClick={() => onOpenBook(book.id)}>
            <BookOpen size={16} /> {book.title}
          </button>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Style it**

Create `src/views/chat/chat.module.css`:
```css
.page { min-height: 100vh; display: flex; align-items: center; justify-content: center;
        background: var(--bg); padding: 40px 20px; }
.center { width: 100%; max-width: 560px; display: flex; flex-direction: column; gap: 28px; }

.hero { display: flex; flex-direction: column; align-items: center; gap: 10px; text-align: center; }
.logoMark { width: 52px; height: 52px; border-radius: 16px; display: grid; place-items: center;
  background: linear-gradient(145deg, oklch(0.28 0.12 264), oklch(0.20 0.10 290));
  border: 1px solid oklch(0.38 0.14 264 / 0.5); color: oklch(0.85 0.15 264);
  box-shadow: 0 0 32px oklch(0.55 0.22 264 / 0.2), inset 0 1px 0 oklch(1 0 0 / 0.08); }
.name { font-size: 30px; font-weight: 800; color: var(--ink); letter-spacing: -0.04em; margin: 0; }
.tagline { font-size: 14px; color: var(--faint); margin: 0; }

.form { display: flex; flex-direction: column; gap: 10px; }
.input { width: 100%; box-sizing: border-box; background: var(--raised);
  border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px;
  font-size: 15px; color: var(--ink); font-family: inherit; line-height: 1.6;
  resize: none; outline: none; transition: border-color 140ms ease, box-shadow 140ms ease; }
.input::placeholder { color: var(--faint); }
.input:focus { border-color: oklch(0.55 0.18 264 / 0.7); box-shadow: 0 0 0 3px oklch(0.55 0.18 264 / 0.1); }

.styleRow { display: flex; gap: 6px; flex-wrap: wrap; }
.pill { padding: 6px 13px; border-radius: 100px; font-size: 12px; font-weight: 500;
  font-family: inherit; background: var(--raised); border: 1px solid var(--border);
  color: var(--muted); cursor: pointer; transition: background 120ms ease, color 120ms ease; }
.pill:hover { color: var(--ink); }
.pill:active { transform: scale(0.96); }
.pillActive { background: oklch(0.22 0.07 264); border-color: oklch(0.42 0.14 264 / 0.7);
  color: oklch(0.80 0.14 264); }

.send { width: 100%; padding: 13px; border: none; border-radius: 12px; background: var(--indigo);
  color: #fff; font-size: 15px; font-weight: 700; font-family: inherit; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: opacity 150ms ease, transform 150ms var(--ease-out); }
.send:hover:not(:disabled) { opacity: 0.9; }
.send:active:not(:disabled) { transform: scale(0.985); }
.send:disabled { opacity: 0.45; cursor: not-allowed; }

.resultCard { display: flex; align-items: center; gap: 8px; padding: 14px 16px;
  background: var(--raised); border: 1px solid var(--border); border-radius: 12px;
  color: var(--ink); font-size: 14px; font-weight: 600; font-family: inherit;
  cursor: pointer; text-align: left; }
.resultCard:hover { border-color: oklch(0.42 0.14 264 / 0.7); }
```

- [ ] **Step 3: Wire up routing**

Replace `src/App.tsx`. **Keep the `EngineGate` wrapper from Task 6** — it owns the "engine down → Restart" screen, and dropping it here would silently lose that behaviour:
```tsx
import { useState } from 'react'
import { EngineGate } from './components/engine-gate/engine-gate'
import { ChatView } from './views/chat/chat'
import { LibraryView } from './views/library/library'
import { ReaderView } from './views/reader/reader'

type Route =
  | { name: 'chat' }
  | { name: 'library' }
  | { name: 'reader'; id: number }

function Router() {
  const [route, setRoute] = useState<Route>({ name: 'chat' })

  if (route.name === 'reader') {
    return <ReaderView id={route.id} onBack={() => setRoute({ name: 'library' })} />
  }
  if (route.name === 'library') {
    return <LibraryView onOpenBook={id => setRoute({ name: 'reader', id })} />
  }
  return <ChatView onOpenBook={id => setRoute({ name: 'reader', id })} />
}

export function App() {
  return (
    <EngineGate>
      <Router />
    </EngineGate>
  )
}
```
A state machine is enough — the app has three screens. A router library would be dead weight. The `Probe` component from Task 6 is deleted; it existed only to prove connectivity.

- [ ] **Step 4: Generate a real book end to end**

Run:
```bash
npm run tauri dev
```
Type `Write a 6 page book about Ancient Rome` and press Enter.

Expected: the reader opens; the stage label moves through "Researching…" → "Creating outline…" → "Writing chapter 1/N…"; prose types itself into the right panel at a readable pace with a blinking caret; the left panel shows "Writing the story…". Because the image provider is the placeholder, pages finish with no illustration — **that is correct for Phase 1**.

- [ ] **Checkpoint:** commit `src/views/chat/` and `src/App.tsx`. **This is the first fully working desktop build — a good place to tag.**

---

## Task 17: Freeze the engine with PyInstaller

Do this **now**, not at the end. Frozen binaries routinely work in dev and fail when bundled; finding that out on ship day is the classic mistake.

**Files:**
- Create: `engine.spec`
- Modify: `package.json`, `backend/requirements.txt`

- [ ] **Step 1: Add PyInstaller**

Run:
```bash
cd backend && venv/Scripts/pip install pyinstaller && venv/Scripts/pip freeze | grep -i pyinstaller
```
Then append `pyinstaller==6.11.1` to `backend/requirements.txt`.

- [ ] **Step 2: Write the PyInstaller spec**

Create `engine.spec` at the repo root:
```python
# PyInstaller spec — freezes the Python engine into one executable.
# uvicorn loads its protocol implementations dynamically, so PyInstaller cannot
# see them; they must be listed as hidden imports or the frozen binary dies at
# startup with "No module named uvicorn.protocols...".
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan", "uvicorn.lifespan.on",
    "app.main",
] + collect_submodules("duckduckgo_search")

a = Analysis(
    ["backend/app/engine.py"],
    pathex=["backend"],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="pageforge-engine-x86_64-pc-windows-msvc",
    debug=False,
    strip=False,
    upx=False,          # UPX compression triggers antivirus false positives
    console=True,       # engine must keep stdout for the handshake
)
```
The `name` **must** carry the target triple from Task 1 Step 6, or Tauri will not find the sidecar.

- [ ] **Step 3: Add the build script**

In the root `package.json`, add to `scripts`:
```json
    "build:engine": "pyinstaller --clean -y --distpath src-tauri/binaries engine.spec"
```

- [ ] **Step 4: Build the engine**

Run:
```bash
npm run build:engine
```
Expected: `src-tauri/binaries/pageforge-engine-x86_64-pc-windows-msvc.exe` exists (~100–250 MB).

- [ ] **Step 5: Smoke-test the frozen binary directly**

This is the step that catches missed hidden imports.

Run:
```bash
src-tauri/binaries/pageforge-engine-x86_64-pc-windows-msvc.exe
```
Expected: it prints one JSON line like `{"ready": true, "port": 53124, "token": "..."}` and keeps running. Press Ctrl+C to stop.

If it crashes with `No module named X`, add `X` to `hiddenimports` in `engine.spec` and rebuild. **Do not move on until this prints the handshake.**

**The failure this actually caught:**

```
ImportError: attempted relative import with no known parent package
```

`engine.py` ended with `from .main import app`. That works under `python -m app.engine`, where the file has a parent package — but PyInstaller runs it as `__main__` with no package, so the relative import fails. Every test passed and dev ran fine; only the frozen binary broke.

Use an absolute import in the entry point:
```python
from app.main import app   # not `from .main import app`
```

This is why the task says to freeze *now* rather than on ship day: the entry point is the one file whose import context differs between dev and frozen, and nothing else surfaces it.

Also set `--distpath` explicitly — PyInstaller defaults to `dist/`, which is where Vite builds the frontend:
```bash
pyinstaller engine.spec --distpath src-tauri/binaries --workpath build/pyinstaller --noconfirm
```

- [ ] **Checkpoint:** commit `engine.spec`, `package.json`, `requirements.txt`. Add `src-tauri/binaries/` and `build/` to `.gitignore` — never commit the binary.

---

## Task 18: Bundle the installer

**Files:**
- Modify: `src-tauri/tauri.conf.json`

- [ ] **Step 1: Register the sidecar**

In `src-tauri/tauri.conf.json`, inside `bundle`, add:
```json
    "externalBin": ["binaries/pageforge-engine"]
```
Write the name **without** the triple suffix and without `.exe` — Tauri appends the right one per platform automatically.

- [ ] **Step 2: Build the installer**

Run:
```bash
npm run build:engine && npm run tauri build
```
`build:engine` must run first; `tauri build` only bundles a binary that already exists.

Expected: an installer at `src-tauri/target/release/bundle/msi/Pageforge_0.1.0_x64_en-US.msi`.

- [ ] **Step 3: Install and run it as a real user would**

Install the `.msi`, launch Pageforge from the Start menu, and generate a 6-page book.

Expected: it works identically to dev. This proves the **release** path — the frozen sidecar, not the venv — because `cfg!(debug_assertions)` is false in a release build.

- [ ] **Step 4: Confirm no orphan process**

Close the app, then run:
```bash
tasklist | grep -i pageforge-engine
```
Expected: nothing. The engine died with the shell.

- [ ] **Checkpoint:** commit `tauri.conf.json`.

---

## Task 19: Delete the dead web stack

Do this **last**, only after the installed app works. Deleting earlier destroys your fallback.

**Files:**
- Delete: `frontend/`, `docker-compose.yml`, `nginx/`, `frontend/Dockerfile`, `backend/Dockerfile`, the stray jpeg
- Modify: `README.md`

- [ ] **Step 1: Confirm nothing still references the old frontend**

Run:
```bash
grep -rniE "frontend/|docker-compose|nginx" --include="*.ts" --include="*.tsx" --include="*.json" --include="*.rs" --exclude-dir=node_modules --exclude-dir=target . | grep -v "^./docs"
```
Expected: no results outside `docs/`. If anything appears, fix it before deleting.

- [ ] **Step 2: Delete the dead files**

```bash
rm -rf frontend/ nginx/ docker-compose.yml backend/Dockerfile
rm -f c8b14100-b0cf-11ea-9d13-fc41ec605dfd.jpeg
```
`frontend/Dockerfile` disappears with `frontend/`.

⚠️ This permanently ends the ability to redeploy `187.127.189.33:8080`. That was approved in the spec.

**`backend/` is NOT deleted** — it is now the engine, and `backend/venv/` is required for the dev loop.

- [ ] **Step 3: Rewrite the README**

Replace `README.md` with:
```markdown
# Pageforge

Offline-first AI book generator. Tauri desktop shell (Rust) + Python engine + React UI.

## Architecture

- `src/` — React + Vite UI (runs in the Tauri WebView)
- `src-tauri/` — thin Rust shell: opens the window, spawns/supervises the Python engine
- `backend/` — **the engine.** FastAPI + the generation pipeline. All AI, RAG, and
  future PDF/image work lives here.

Rust never touches AI logic. It spawns Python, reads a one-line JSON handshake
(`{ready, port, token}`) from its stdout, and hands `{port, token}` to the UI.
The engine listens on 127.0.0.1 on an OS-assigned port and requires a bearer token,
so nothing is exposed off-machine.

## Setup (once)

1. Node 20+
2. [Ollama](https://ollama.com) — `ollama pull llama3.1`
3. Rust — https://rustup.rs (then reopen your terminal)
4. MSVC C++ Build Tools — tick "Desktop development with C++"
5. `cd backend && python -m venv venv && venv/Scripts/pip install -r requirements.txt`
6. `npm install`

## Run

```bash
npm run tauri dev
```

The first run takes 5–15 minutes while Rust compiles once. Later runs take seconds.

- Edit React/CSS → instant hot reload
- Edit Python → restart the app (seconds, no rebuild)
- Edit Rust → recompile (~10–60s, rare)

## Build an installer

```bash
npm run build:engine   # PyInstaller → src-tauri/binaries/
npm run tauri build    # → src-tauri/target/release/bundle/
```

`build:engine` must run first. macOS builds require a Mac.

## Tests

```bash
cd backend && venv/Scripts/python.exe -m pytest tests/ -v
```

## Roadmap

- **Phase 2** — PDF/EPUB export
- **Phase 3** — offline knowledge via local ZIM files (`libzim`); becomes the default
  knowledge provider, replacing DuckDuckGo
- **Later** — local image generation (FLUX.1 Schnell / Z Image Turbo) via the existing
  `ImageProvider` seam
```

- [ ] **Step 4: Full verification**

Run:
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/ -v
```
Expected: all pass.

Run:
```bash
npm run tauri dev
```
Expected: generate a book successfully.

- [ ] **Checkpoint:** commit the deletions and the README. **Phase 1 complete.**

---

## Definition of done

- [ ] `npm run tauri dev` opens a window and auto-starts the engine — no manual `uvicorn`
- [ ] Typing "Write a 6 page book about Ancient Rome" streams prose live at a readable pace
- [ ] Library and Reader work; the typewriter pacing is unchanged from the web version
- [ ] Books, chats, and settings persist in the OS app-data directory
- [ ] Requests without the token get 401; the WebSocket rejects a bad token
- [ ] A broken engine shows "The engine stopped" + the reason + a working Restart button — never an infinite spinner
- [ ] A single malformed LLM response retries once instead of killing the book
- [ ] A DuckDuckGo outage degrades to no-research instead of failing the generation
- [ ] Closing the app leaves no orphan `python.exe` / `pageforge-engine.exe`
- [ ] `npm run build:engine && npm run tauri build` produces an `.msi` that works when installed
- [ ] `pytest tests/ -v` passes
- [ ] No Docker, nginx, or Next.js remains; `backend/` is intact
- [ ] Adding a provider is one new file + one factory line

---

## Known deviations from `UPDATE3.md`

Recorded so nothing is a surprise at review:

1. **"Do NOT use a Python backend" is knowingly overridden.** Rationale in the spec: FLUX/diffusers and `libzim` are Python-only in practice. "No Electron", "no cloud backend", and "everything local" are all still honored.
2. **Phase 1 is not fully offline when research is on** — DuckDuckGo remains the default `KnowledgeProvider` until Phase 3 swaps in ZIM.
3. **No images render** — `ImageProvider` returns `None` by design; prompts are still generated and stored per page.
4. **PDF/EPUB export is not built** — it does not exist today (contrary to `UPDATE3.md`'s claim) and is Phase 2.
