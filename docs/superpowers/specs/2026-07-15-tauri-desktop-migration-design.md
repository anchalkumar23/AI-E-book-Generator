# Tauri Desktop Migration — Phase 1 Design

**Created:** 2026-07-15
**Revised:** 2026-07-16 — **architecture pivot (v2): Tauri shell + Python engine sidecar.** Supersedes the v1 all-Rust-pipeline design.
**Status:** Awaiting approval
**Source requirement:** `UPDATE3.md`

---

## Goal

Convert Pageforge from a two-process web app (Python FastAPI + Next.js, deployed via Docker) into a single cross-platform **Tauri desktop application** that runs entirely on the user's machine, with a ChatGPT-style chat interface driving live book generation.

**Division of labour:** Rust/Tauri owns only the desktop shell, native APIs, and application lifecycle. **All AI generation, RAG, PDF creation, and future image generation stay in Python.**

---

## Revision note: why v1 was discarded

v1 specified porting the entire generation pipeline to Rust. That design was abandoned on 2026-07-16. The reasoning, recorded because it is the most consequential decision in this project:

1. **The image roadmap makes Python unavoidable.** The approved plan is FLUX.1 Schnell / Z Image Turbo. Those are PyTorch + `diffusers`. Rust's `candle` cannot realistically run them today. A Rust pipeline would have to be rewritten in Python the moment image generation landed.
2. **ZIM support is solved in Python and unsolved in Rust.** Verified: [`libzim`](https://pypi.org/project/libzim/) 3.11.0 is maintained by **openZIM** — the authors of the ZIM format — with prebuilt wheels for Windows x64 and macOS arm64/x86_64. v1 listed "ZIM in Rust is unproven, fallback is C++ FFI" as a top risk. That risk disappears entirely.
3. **DuckDuckGo scraping in Rust was v1's #1 risk.** Python keeps the working `duckduckgo-search` library. Risk disappears.
4. **Phase 2 (PDF/EPUB) becomes tractable** — `reportlab` / `weasyprint` / `ebooklib` are mature; Rust equivalents are weak.
5. **The existing pipeline already works.** A rewrite reintroduces solved bugs for no benefit.
6. **Maintainability.** The project owner does not know Rust. This confines Rust to a thin shell that is rarely opened.

### Accepted deviation from `UPDATE3.md`

`UPDATE3.md` states, explicitly and separately from its "no cloud backend" rule: **"Do NOT use a Python backend."** This design knowingly overrides that line.

- **Still honored:** "Do NOT use Electron", "Do NOT use any cloud backend", "Everything should run locally". Nothing leaves the machine; nothing is publicly exposed.
- **Violated:** the literal "no Python backend" clause.
- **Risk:** if `UPDATE3.md` is a client acceptance document, this could fail acceptance regardless of engineering merit. This was raised with the project owner and the override was chosen deliberately.

---

## Context: what actually exists today

`UPDATE3.md` describes the current project inaccurately. Verified against the codebase:

| `UPDATE3.md` claims | Verified reality |
| --- | --- |
| "PDF/EPUB export" | **Does not exist.** Zero pdf/epub references in `backend/` or `frontend/`. Net-new (Phase 2). |
| "Chat interface" | **Does not exist.** Current UI is form-based. Net-new (Phase 1). |
| "AI book generation using Ollama" | **Partly.** Groq is primary (`llm.py`); Ollama is an untested fallback. |
| "WebSocket streaming" | ✅ Exists (`ws_manager.py`). **Preserved by this design.** |
| "SQLite database" | ✅ Exists (SQLModel). |
| "Library system" | ✅ Exists. |

**Other `UPDATE3.md` contradictions and their resolutions:**

1. *"no cloud backend"* vs *"Ollama/groq API"* — Groq is cloud. **Resolved:** Ollama is default; Groq is opt-in via settings.
2. *"real time chat and image generated just like chatgpt"* vs *"Do NOT implement image generation yet"* — **Resolved:** no images render in Phase 1; an `ImageProvider` seam is built instead.
3. *"no cloud"* vs the existing DuckDuckGo research — **Resolved:** DuckDuckGo remains the default `KnowledgeProvider` until ZIM replaces it in Phase 3. **Phase 1 is therefore not fully offline when research is enabled.** Knowing, temporary trade.

**Developer machine (verified):** Node v20.19.2 ✅, Ollama v0.32.0 with `llama3.1`/`llama3`/`gemma:2b` ✅, Python + `backend/venv` ✅, **Rust not installed** ❌, **MSVC C++ Build Tools not installed** ❌.

---

## Scope: three phases

| Phase | Contents | Status |
| --- | --- | --- |
| **Phase 1** | Tauri shell, Python engine sidecar, React+Vite frontend, chat UI, provider seams, SQLite | **This spec** |
| **Phase 2** | PDF/EPUB export (video export placeholder) | Later spec |
| **Phase 3** | ZIM local knowledge via `libzim`; becomes default `KnowledgeProvider` | Later spec |

---

## Approved decisions

| Area | Decision |
| --- | --- |
| Execution | Tauri 2 desktop shell. No Electron. |
| AI / RAG / PDF / images | **Stay in Python.** Rust does not touch them. |
| Transport | **Loopback HTTP + WebSocket**, FastAPI preserved, `127.0.0.1` on an OS-assigned port, bearer-token authenticated |
| LLM | `LlmProvider` ABC — **Ollama default**, Groq opt-in |
| UI | **Chat is the main surface**; Library grid + flipbook Reader preserved |
| Chat history | **Multiple threads** (ChatGPT-style), persisted in SQLite |
| Images | `ImageProvider` ABC — placeholder impl. **Pollinations removed.** Prompts still generated + stored per page. FLUX.1 Schnell / Z Image Turbo integrate later with minimal change. |
| Knowledge | `KnowledgeProvider` ABC — **DuckDuckGo default temporarily**; ZIM becomes default in Phase 3 |
| Repo layout | Root-level Tauri (`src/` + `src-tauri/`); `backend/` becomes the engine; Next.js deleted |
| Credits | **Removed** — SaaS billing concept, meaningless locally |

---

## Architecture

### Three components

```
┌──────────────────────────────────────────────────┐
│  Tauri shell (Rust — thin, rarely touched)       │
│  • window + WebView                              │
│  • spawn / supervise / kill the Python engine    │
│  • read handshake, expose engine_info to the UI  │
│  • native file dialogs (Phase 2: Save PDF)       │
│  • lifecycle, single-instance, updater           │
└───────────────┬──────────────────────────────────┘
                │ spawns, reads stdout
                ▼
┌──────────────────────────────────────────────────┐
│  Python engine (FastAPI — all the real work)     │
│  • generation pipeline    • RAG / knowledge      │
│  • LLM providers          • image providers      │
│  • SQLite                 • WebSocket streaming  │
│  • Phase 2: PDF/EPUB      • Phase 3: libzim      │
│  binds 127.0.0.1:<ephemeral>, token-authed       │
└───────────────▲──────────────────────────────────┘
                │ HTTP + WebSocket (loopback only)
                │
┌───────────────┴──────────────────────────────────┐
│  React + Vite frontend (in the WebView)          │
│  • chat / library / reader                       │
└──────────────────────────────────────────────────┘
```

Rust never touches AI logic. It is a process supervisor with a window attached.

### Startup handshake

Solves port conflicts and local-app snooping without hardcoding anything.

1. Engine binds `127.0.0.1:0` — the OS assigns a free port.
2. Engine generates a random 32-byte token (`secrets.token_urlsafe`).
3. Engine prints **exactly one line** of JSON to stdout and flushes:
   `{"ready": true, "port": 53124, "token": "..."}`
4. Rust reads stdout via `CommandEvent::Stdout`, parses that line, stores `{port, token}` in Tauri state.
5. Rust shows the window (a splash covers steps 1–4).
6. Frontend calls `invoke("engine_info")` → `{port, token}` and uses it for every HTTP/WS call.
7. If no handshake within **30 seconds**, Rust shows a fatal error instead of hanging.

**Authentication:** every request carries `Authorization: Bearer <token>`. FastAPI middleware rejects anything else with 401. WebSocket passes the token as a query parameter (browsers cannot set WS headers). This prevents other local processes from driving the engine.

**Shutdown:** Rust kills the child on `RunEvent::Exit`. As a backstop against orphans, the engine watches stdin — when the parent dies, stdin closes and the engine exits itself.

### Dev vs production spawn

| Mode | Rust spawns |
| --- | --- |
| **Dev** (`cfg!(debug_assertions)`) | `backend/venv/Scripts/python.exe -m app.engine` directly — no freezing, instant Python edits |
| **Production** | The PyInstaller-frozen sidecar binary via `app.shell().sidecar("pageforge-engine")` |

This keeps the dev loop fast. Python changes need only an app restart, never a rebuild.

**Sidecar filename requirement:** Tauri requires a target-triple suffix. On Windows the frozen binary must be named:
`src-tauri/binaries/pageforge-engine-x86_64-pc-windows-msvc.exe`
Get the triple with `rustc --print host-tuple`. A missing/incorrect suffix is the most common sidecar failure.

### Python engine layout (`backend/app/`)

Existing files are refactored, not rewritten. `generator.py`, `ws_manager.py`, `database.py`, and `routers/books.py` keep working.

```
engine.py          NEW — bootstrap: pick port, mint token, print handshake, watch stdin
main.py            MODIFIED — bind 127.0.0.1, token middleware, Tauri CORS origins
auth.py            NEW — bearer-token middleware + WS token check
database.py        unchanged
models/
  book.py          unchanged
  chat.py          NEW — Chat + Message
routers/
  books.py         mostly unchanged
  chats.py         NEW — chat threads + messages
  settings.py      NEW — provider selection, model names, API keys
  credits.py       DELETED
services/
  generator.py     unchanged pipeline; calls providers via factories
  llm/
    base.py        NEW — LlmProvider ABC
    ollama.py      NEW — default
    groq.py        NEW — opt-in (lifted from today's llm.py)
    factory.py     NEW — settings → provider
  knowledge/
    base.py        NEW — KnowledgeProvider ABC
    duckduckgo.py  NEW — wraps today's search.py
    none.py        NEW — no-op
    factory.py     NEW           (zim.py added in Phase 3)
  images/
    base.py        NEW — ImageProvider ABC
    placeholder.py NEW — returns None
    factory.py     NEW           (flux.py added later)
  llm.py           DELETED — split into llm/
  search.py        DELETED — moved into knowledge/duckduckgo.py
  images.py        DELETED — Pollinations removed, replaced by images/
```

### Provider abstractions

The extension seam. Signatures match today's functions, so `generator.py` changes only at call sites.

```python
class LlmProvider(ABC):
    @abstractmethod
    def stream_json(self, prompt: str, on_token: Callable[[str], None]) -> dict: ...

class KnowledgeProvider(ABC):
    @abstractmethod
    def research(self, topic: str) -> tuple[str, list[dict]]: ...

class ImageProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, book_id: int, page: int) -> str | None: ...
```

Each `factory.py` maps a settings string to an implementation. **Adding ZIM or FLUX later = one new file + one factory entry.** Nothing else changes.

### Rust shell layout (`src-tauri/src/`)

```
main.rs      Tauri builder, plugin init, spawn engine, RunEvent::Exit cleanup
engine.rs    spawn (dev vs sidecar), parse handshake line, 30s timeout, kill child
commands.rs  #[tauri::command] engine_info() -> EngineInfo { port, token }
state.rs     EngineState (Mutex<Option<EngineInfo>>)
```

Requires `tauri-plugin-shell`. That is the entire Rust surface for Phase 1.

### Frontend layout (`src/`)

```
main.tsx
App.tsx              routing + shell
views/
  chat/              NEW — ChatGPT-style home + thread
  library/           ported from library-client.tsx
  reader/            ported from reader-client.tsx
components/          ported: book-card, book-grid, sidebar, topbar, home-screen
lib/
  engine.ts          NEW — invoke("engine_info"), builds base URL + auth header
  api.ts             ported — same calls, dynamic base URL + token
  types.ts           ported
styles/globals.css   ported
```

Components are ~90% framework-agnostic (CSS Modules + `motion` + `@phosphor-icons/react`). The only Next.js coupling is `next/navigation`'s `useRouter`, replaced with lightweight routing. The sidebar credits meter is removed.

**The reader's throttled typewriter logic is preserved verbatim** — token buffer, paced reveal (`step` 4/2/1 at 28 ms), blinking caret, image-left/text-right live layout. Only the WebSocket URL becomes dynamic.

**CORS:** the Tauri WebView origin is `http://tauri.localhost` (Windows) and `tauri://localhost` (macOS). Both are allowed; the current wildcard is removed.

---

## Data model (SQLite via existing SQLModel)

```sql
book(id, title, prompt, book_type, page_count, illustration_style,
     status, cover_hue, favorite, progress, progress_label,
     use_research, writing_style, outline, content,
     error_message, created_at, last_modified)     -- unchanged

chat(id, title, created_at)                         -- NEW

message(id, chat_id, role, content, book_id, created_at)   -- NEW
   -- role: 'user' | 'assistant'
   -- book_id: nullable FK to the book an assistant message produced

setting(key, value)                                 -- NEW
   -- llm_provider = ollama | groq
   -- ollama_model, groq_api_key
   -- knowledge_provider = duckduckgo | none
   -- image_provider = placeholder
```

`book.content` remains a JSON blob with today's shape (pages + illustration prompts), so the Reader needs no data changes.

**Database location:** the OS app-data directory (via Tauri's path API, passed to the engine as an argument), not the current working directory. Ships correctly in an installed app.

Illustration prompts are stored per page, unchanged: scene, characters_present, environment, mood, lighting, composition, style_note.

---

## Data flow — one generation

```
User types "Write a 15 page book about Ancient Rome"
      ↓  POST /api/books  (Bearer token)
Engine returns book immediately; BackgroundTask starts the pipeline
      ↓  frontend opens WS /api/books/{id}/ws?token=…
 1. KnowledgeProvider.research()   → WS: progress "Researching…"
 2. LlmProvider.stream_json()      → WS: progress "Creating outline…"
 3. per chapter: stream_json()     → WS: token ×N        ← live typing
 4. per page: ImageProvider.generate() → WS: page (placeholder → None)
 5. finalize                       → WS: done
```

**Unchanged from today.** Same event vocabulary (`progress`/`token`/`page`/`done`/`error`), same `ws_manager`, same incremental saves for mid-generation recovery. This is the payoff of keeping Python.

**Writing styles** (expository / narrative / descriptive / persuasive) thread through the blueprint prompt and every chapter prompt, as today, maintaining character/timeline/style/topic consistency.

---

## Error handling

| Failure | Behavior |
| --- | --- |
| Engine fails to start / no handshake in 30 s | Rust shows a fatal dialog with captured stderr — never an infinite splash |
| Engine dies mid-session | Rust detects child exit; UI shows "Engine stopped" with a Restart action |
| Ollama not running | *"Ollama isn't running — start it and try again."* |
| Model not pulled | *"Model `llama3.1` not found. Run: `ollama pull llama3.1`"* |
| DuckDuckGo scrape fails | **Degrades gracefully** — logged, generation continues without research. A flaky scraper must never kill a book. |
| LLM returns invalid JSON | Retry once, then WS `error` |
| Pipeline raises | Caught in `run_generation`, saved as `status=error`, emitted as WS `error` |
| Request without valid token | 401 |

---

## Testing

Existing `pytest` infrastructure is retained and extended (`backend/tests/`).

- `test_extract.py` — the `_TextExtractor` state machine (`"text":"` detection, JSON escape handling). Highest-value target.
- `test_providers.py` — a fake `LlmProvider` returning canned JSON; assert the pipeline emits the expected event sequence. The ABCs make this possible for the first time.
- `test_auth.py` — requests without a token get 401; with a token, 200.
- `test_engine.py` — the handshake line is valid JSON with `port` and `token`.
- `test_books.py` — existing, updated for auth.

**No frontend tests** — none exist today; adding infrastructure is out of scope.

---

## File disposition

**Now the engine (was going to be unlinked in v1 — reversed):**
- `backend/` — the Python app is now the core of the product. `venv/` is required for the dev loop.

**Deleted:**

| Path | Reason |
| --- | --- |
| `frontend/` | Only after components are ported to `src/` |
| `docker-compose.yml` | Nothing to orchestrate |
| `nginx/` | No reverse proxy |
| `frontend/Dockerfile`, `backend/Dockerfile` | Nothing containerized |
| `backend/app/services/images.py` | Pollinations removed |
| `backend/app/routers/credits.py` | Credits concept dropped |
| `c8b14100-b0cf-11ea-9d13-fc41ec605dfd.jpeg` | Stray root file, referenced by nothing |

**Accepted consequence:** deleting the Docker/nginx layer permanently ends redeploying the web version at `187.127.189.33:8080`.

---

## How to run it

### One-time setup (Windows)

| # | Requirement | Status |
| --- | --- | --- |
| 1 | Node 20+ | ✅ v20.19.2 |
| 2 | Ollama | ✅ v0.32.0 |
| 3 | Python + `backend/venv` | ✅ exists |
| 4 | WebView2 | ✅ built into Windows 11 |
| 5 | **Rust** | ❌ [rustup.rs](https://rustup.rs) → `rustup-init.exe` → accept defaults → **reopen the terminal** |
| 6 | **MSVC C++ Build Tools** | ❌ [Build Tools for VS](https://visualstudio.microsoft.com/visual-cpp-build-tools/) → tick **"Desktop development with C++"** (~2–4 GB) |

Verify: `rustc --version`, `cargo --version`. Without MSVC, `cargo build` fails with `link.exe not found`.

Rust is needed **only to build the shell**. Day-to-day work is Python and React.

### Daily development

```bash
npm install          # once — frontend deps + Tauri CLI
npm run tauri dev    # replaces "docker compose up"
```

Opens a native window and auto-spawns the Python engine from `backend/venv`. No `localhost:3000`, no manual `uvicorn`, no Docker, no browser.

**The first `npm run tauri dev` takes 5–15 minutes** compiling Rust dependencies once. This is expected, not a hang. Later runs take seconds.

- Edit **React/CSS** → instant hot reload.
- Edit **Python** → restart the app (a few seconds). No recompiling.
- Edit **Rust** → recompile (~10–60 s). Rare.

### Building an installer

```bash
npm run build:engine   # PyInstaller → src-tauri/binaries/pageforge-engine-<triple>.exe
npm run tauri build    # bundles shell + engine into one .msi/.exe
```

`build:engine` must run first — `tauri build` only bundles a binary that already exists. **macOS builds require a Mac** (cross-compiling is not possible); the sidecar must also be codesigned and notarized there.

---

## Risks

1. **PyInstaller bundling is the main new risk.** Hidden imports and data files commonly get missed, producing a binary that works in dev and fails when frozen. Mitigated by making `build:engine` + a smoke-run part of the workflow early, not at the end.
2. **Installer size.** The frozen engine is ~100–250 MB, eroding Tauri's small-binary advantage. With torch (future FLUX), installers reach multiple GB — that will likely require downloading models on first run rather than bundling them.
3. **Antivirus false positives** on PyInstaller binaries on Windows are common and may require codesigning.
4. **Orphaned engine processes** if the shell is killed uncleanly. Mitigated by the stdin-watchdog backstop.
5. **DuckDuckGo scraping** remains inherently fragile (though the Python library is far more robust than a hand-rolled Rust scraper). Removed in Phase 3.
6. **`UPDATE3.md` acceptance risk** — see "Accepted deviation" above.

---

## Out of scope (Phase 1)

- PDF/EPUB export (Phase 2); video export remains a placeholder thereafter
- ZIM knowledge base (Phase 3)
- Any image rendering — only the `ImageProvider` seam and stored prompts
- Frontend test infrastructure
- macOS CI builds, codesigning, auto-update

---

## Appendix: ZIM files to download now (Phase 3 prep)

Collecting these during Phase 1 is zero-risk. Skip all `maxi` variants — they bundle Wikipedia photos, useless because the app generates its own illustrations.

**Recommended set (~18 GB):**

| File | Size | Purpose |
| --- | --- | --- |
| `wikipedia_en_all_mini_2026-06.zim` | 12 GB | Intro paragraphs of every article — best coverage-to-size; matches the research use case |
| `wikipedia_en_top_nopic_2026-06.zim` | 2.1 GB | Full text of top ~50k articles — depth for common topics |
| `wikibooks_en_all_nopic_2026-04.zim` | 3.3 GB | How-to content for tutorial/guide/educational book types |
| `wikipedia_en-simple_all_mini_2026-06.zim` | 450 MB | Simple English — serves the children's book type |

**Minimal test set (~2.5 GB):** `wikipedia_en_top_nopic_2026-06.zim` + `wikipedia_en-simple_all_mini_2026-06.zim`

**Sources:** browse [library.kiwix.org](https://library.kiwix.org); download from `https://lb.download.kiwix.org/zim/wikipedia/` and `/zim/wikibooks/`. Use the `.zim.torrent` for the 12 GB file — resumable downloads matter at that size.

**Reader:** `libzim` 3.11.0 (openZIM official, Windows x64 + macOS wheels) — `pip install libzim`, `Archive` class with search support.
