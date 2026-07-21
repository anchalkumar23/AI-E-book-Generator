import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

# Anchored to this file, not the CWD: the Tauri shell spawns the engine from its
# own directory, so a bare load_dotenv() finds nothing and keys go missing.
# Absent in the frozen app by design — there the key comes from Settings.
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .auth import token_middleware
from .database import create_db
from .routers import books, chats, settings

STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    print(json.dumps({
        "ready": True,
        "port": int(os.environ["ENGINE_PORT"]),
        "token": os.environ["ENGINE_TOKEN"],
    }), flush=True)
    yield


app = FastAPI(title="AI E-Book Generator API", lifespan=lifespan)

# The WebView origin differs per OS, and in dev the frontend is served by Vite
# on 1420 — omitting that origin makes every dev request fail as "Failed to
# fetch". CORS is not the security boundary here; the bearer token is, and the
# server only listens on 127.0.0.1.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://tauri.localhost",   # Windows production
        "tauri://localhost",        # macOS/Linux production
        "http://localhost:1420",    # Vite dev server
        "http://127.0.0.1:1420",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(token_middleware)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(books.router,    prefix="/api/books",    tags=["books"])
app.include_router(chats.router,    prefix="/api/chats",    tags=["chats"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
