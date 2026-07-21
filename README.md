# Pageforge — AI E-Book Generator

A desktop app that writes illustrated ebooks. Describe a book, and it researches,
writes, and illustrates it while you watch the text stream in.

Windows desktop app: a Tauri (Rust) shell hosting a React UI, supervising a
Python engine that does the generation.

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│  Tauri shell (Rust)                              │
│    • owns the window                             │
│    • spawns + supervises the Python engine       │
│    • hands the frontend the port and token       │
│                                                  │
│  ┌────────────────────────┐                      │
│  │  WebView (React + Vite)│                      │
│  │    Chat → Library → Reader                    │
│  └───────────┬────────────┘                      │
│              │ HTTP + WebSocket (127.0.0.1)      │
│              ▼                                   │
│  ┌────────────────────────┐                      │
│  │  Engine (Python)       │                      │
│  │    FastAPI + SQLite    │                      │
│  │    LLM / research / images                    │
│  └────────────────────────┘                      │
└──────────────────────────────────────────────────┘
```

**Why a separate process instead of rewriting the generator in Rust?** The
generation logic is Python and works. The shell only needs to own a window and
keep a child process alive.

Three details make it safe:

- **The port is chosen at runtime.** The engine binds port 0, the OS assigns a
  free one, and the engine reports it back on stdout. A hardcoded port collides
  with whatever else the user is running.
- **Every request carries a bearer token** generated per launch. The engine
  listens on loopback, but that is still reachable by other local processes; the
  token is what stops them. Only the shell learns it, from the handshake.
- **The engine dies with the shell.** It watches stdin for EOF and exits, so
  closing the window never leaves a stray server behind.

The handshake is one JSON line on stdout:

```json
{"ready": true, "port": 59767, "token": "ha25TyP…"}
```

---

## Running it

**Requirements:** Node 18+, Rust (stable), Python 3.11+

```bash
# 1. Frontend deps
npm install

# 2. Python engine
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
cd ..

# 3. Add a Groq API key (free at console.groq.com)
#    Create backend/.env with:
#      GROQ_API_KEY=gsk_…
#    Or set it in the app's Settings once running.

# 4. Run the app
npm run tauri dev
```

A window opens. `npm run tauri dev` starts everything — Vite, the Rust shell,
and the Python engine — so it is the only command you need.

The first Rust build compiles ~250 crates and takes several minutes. Later
builds only recompile the app's own files and take seconds.

**Expected startup output:**

```
VITE v6.4.3  ready in 535 ms
  ➜  Local:   http://localhost:1420/
   Running DevCommand (`cargo run …`)
    Finished `dev` profile in 0.86s
     Running `target\debug\app.exe`
```

The engine needs a few seconds to import FastAPI and its providers before the
window has data; on a machine short on RAM it can take considerably longer.

### Tests

```bash
cd backend && venv\Scripts\activate
pytest tests/ -q         # 55 passed
```

```bash
npx tsc --noEmit         # frontend typecheck
```

### Stopping it

Close the window, or press `Ctrl+C` in the terminal. Both shut the engine down
with the shell.

Killing the terminal without closing the window can leave the Vite dev server
holding port 1420 and an engine running. See the next section.

---

## Building the installer

```bash
npm run build:app
```

That freezes the Python engine and then builds the Windows installer, which
lands in `src-tauri/target/release/bundle/nsis/`.

The two halves can be run separately:

```bash
npm run build:engine    # PyInstaller -> src-tauri/binaries/ (~25 MB)
npx tauri build         # bundles the shell + engine into an installer
```

**The engine ships as a sidecar.** PyInstaller freezes it into
`pageforge-engine-x86_64-pc-windows-msvc.exe` — the target-triple suffix is
required, since that is how Tauri resolves sidecars. `bundle.externalBin` in
`tauri.conf.json` pulls it into the installer, and the user needs no Python.

**Always smoke-test the frozen engine before bundling:**

```bash
src-tauri/binaries/pageforge-engine-x86_64-pc-windows-msvc.exe <some-dir>
```

It must print one line — `{"ready": true, "port": …, "token": …}` — and keep
running. A frozen binary can fail where dev works, because dynamically loaded
imports are invisible to PyInstaller's analysis and the entry point runs as
`__main__` with no parent package. Both bit during development.

An installed build has no `.env`, so API keys are entered in **Settings** and
stored in the app database.

---

## Troubleshooting

**`Port 1420 is already in use`**

A previous run's dev server is still alive. Find and stop it:

```powershell
# Who holds the port
Get-NetTCPConnection -LocalPort 1420 -State Listen | Select-Object OwningProcess

# Stop everything this project left behind
Get-Process | Where-Object { $_.Path -like '*AI E-Book Generator*' } | Stop-Process -Force
```

On Windows, prefer PowerShell's `Stop-Process` over `taskkill` — under memory
pressure `taskkill` times out where `Stop-Process` still works.

**Changes to Python code do nothing**

The engine is spawned once when the app launches. Vite hot-reloads the frontend
and Tauri watches Rust, but nothing watches Python — restart the app after
editing anything under `backend/`.

**`Model 'x' not found. Run: ollama pull x`**

The provider is set to Ollama and the named model isn't installed. Either
`ollama pull` it, or switch to Groq (the default). Check what you have with
`ollama list`.

**Generation fails with an Ollama memory error**

`unable to allocate CUDA_Host buffer` means the model doesn't fit in RAM. An 8B
model needs roughly 5 GB free. Use a smaller model (`gemma:2b`) or Groq.

**The window is blank or shows an engine error**

The engine failed to start. Its stdout/stderr go to the terminal running
`npm run tauri dev` — the traceback will be there.

---

## Settings

Sidebar → **Settings** configures the LLM provider, model, and API keys without
touching files. Values are stored in the app's database, which is how the
packaged app is configured — an installed build has no `.env`.

Resolution order is **database → environment → default**, so a key saved in
Settings overrides `.env`. The Settings screen shows the *effective* value
rather than a blank, so opening it and saving can't wipe a key that came from
the environment.

---

## Configuring the LLM

Generation defaults to **Groq** (cloud). Set a key in Settings, or for
development put one in `backend/.env`:

```
GROQ_API_KEY=gsk_…
GROQ_MODEL=llama-3.3-70b-versatile
```

**Ollama** works too for offline use — set `llm_provider` to `ollama`. Be aware
that an 8B model needs roughly 5 GB of free RAM; on a smaller machine Ollama
fails with `unable to allocate CUDA_Host buffer` and Groq is the better choice.

---

## Illustrations

Off until you add a token — books generate text-only and nothing fails.

To turn them on, create a free token at
[huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (no
card needed) and add it to `backend/.env`:

```
HF_TOKEN=hf_…
```

Images render through **Stable Diffusion 3 Medium** on Hugging Face's serverless
inference — roughly 17s per image, measured.

Not FLUX: Hugging Face deprecated FLUX.1-schnell on the free `hf-inference`
provider (it now returns `410 no longer supported`) and moved it to paid
partners. SD3-medium is currently the only text-to-image model the free tier
serves. If images start failing, check what's left and set `HF_MODEL`:

```
GET https://huggingface.co/api/models?pipeline_tag=text-to-image&inference_provider=hf-inference
```

The model sleeps when idle, so the first call of a session can return 503 with a
wake estimate; the provider waits and retries once.

Generated images are downloaded into `backend/static/images/<book_id>/` rather
than hotlinked, so a finished book still reads with no internet.

Two other providers exist behind the same interface:

| Provider | Notes |
|---|---|
| `huggingface` | Default. Free tier, needs `HF_TOKEN`. |
| `pollinations` | Was keyless; moved to paid credits in 2026 and now 402s without a funded key. Set `POLLINATIONS_TOKEN` to use it. |
| `placeholder` | Generates prompts but no images. |

A failed illustration never fails the book — the page keeps its text and records
why the image is missing.

Groq is reached over plain HTTP via `httpx` rather than the official SDK — the
SDK hung indefinitely on `create()` during development while a direct POST to
the same endpoint returned in 0.7s.

---

## Project layout

```
├── src/                      React frontend
│   ├── App.tsx               routing between the three screens
│   ├── views/
│   │   ├── chat/             the composer — describe a book
│   │   ├── library/          grid of books, live progress
│   │   └── reader/           page view + streaming typewriter
│   ├── components/           sidebar, topbar, cards, engine gate
│   └── lib/
│       ├── engine.ts         talks to Rust for port + token
│       └── api.ts            HTTP client
│
├── src-tauri/                Rust shell
│   └── src/
│       ├── engine.rs         spawn, handshake, shutdown
│       ├── state.rs          engine status shared with the frontend
│       ├── commands.rs       commands the frontend can invoke
│       └── lib.rs            wiring
│
├── backend/                  Python engine
│   ├── app/
│   │   ├── engine.py         entry point: port 0, token, handshake
│   │   ├── auth.py           bearer-token middleware
│   │   ├── main.py           FastAPI app
│   │   ├── routers/          books, chats, settings
│   │   └── services/
│   │       ├── generator.py  the generation pipeline
│   │       ├── llm/          groq, ollama
│   │       ├── knowledge/    research providers
│   │       └── images/       illustration providers
│   └── tests/
│
└── engine.spec               PyInstaller build for the frozen engine
```

---

## Build notes

Things that cost real time during development, recorded so they don't again:

- **Disk.** The Rust build needs ~5 GB free. A full disk surfaces first as
  `no space on device` and then as a misleading `STATUS_ACCESS_VIOLATION`, which
  looks like a compiler bug. Package caches are usually the culprit, not the
  project — `pip cache purge` reclaimed 19 GB here.
- **A crate can be left corrupt** if the disk fills mid-build. That produced
  `STATUS_STACK_BUFFER_OVERRUN` on every later build until the crate was deleted
  from `~/.cargo/registry` and re-fetched.
- **Memory.** The default dev profile's full debug info made LLVM run out of
  memory. `[profile.dev] debug = 0` fixes it, and `cargo build -j 1` keeps peak
  usage down on small machines.
- **CORS preflight must skip auth.** Browsers send no `Authorization` header on
  the preflight `OPTIONS`, so rejecting it makes every request from the WebView
  fail as `Failed to fetch`. Since any request with an auth header triggers
  preflight, this breaks the entire API rather than one endpoint.
