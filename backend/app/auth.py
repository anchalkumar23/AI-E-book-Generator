"""Bearer-token auth for the loopback engine.

Only the Tauri shell knows the token (it read it from the handshake), so other
local processes cannot drive the engine.
"""
import os

from fastapi import Request
from fastapi.responses import JSONResponse

PUBLIC_PREFIXES = ("/static",)


async def token_middleware(request: Request, call_next):
    # Browsers never send Authorization on a CORS preflight, so rejecting OPTIONS
    # here makes every browser request fail as "Failed to fetch". Preflights
    # carry no data and are answered by the CORS middleware.
    if request.method == "OPTIONS" or request.url.path.startswith(PUBLIC_PREFIXES):
        return await call_next(request)

    expected = os.environ.get("ENGINE_TOKEN", "")
    if request.headers.get("authorization") != f"Bearer {expected}":
        return JSONResponse({"detail": "unauthorized"}, status_code=401)

    return await call_next(request)


def ws_token_ok(token: str | None) -> bool:
    """Browsers cannot set WebSocket headers, so the token arrives as a query param."""
    return bool(token) and token == os.environ.get("ENGINE_TOKEN", "")
