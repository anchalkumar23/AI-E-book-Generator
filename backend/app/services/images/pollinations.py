"""Illustrations via Pollinations.

NOTE: Pollinations now bills per image ("pollen"). Anonymous requests fail with
402, so this is only useful with a funded key — set POLLINATIONS_TOKEN. It is
not the default for that reason.

The image is downloaded and stored under static/ rather than hotlinked, so a
generated book still reads offline and doesn't refetch on every page turn.

Returns a path relative to the engine root (`/static/…`), not an absolute URL:
the engine's port changes every launch, so a stored absolute URL would break the
next time the app starts. The frontend resolves it against the current engine.
"""
import os
import urllib.parse
from pathlib import Path

import httpx

from .base import ImageProvider

POLLINATIONS_URL = os.getenv("POLLINATIONS_URL", "https://image.pollinations.ai/prompt")
STATIC_DIR = Path(__file__).resolve().parents[3] / "static"


class PollinationsProvider(ImageProvider):
    def __init__(self, width: int = 768, height: int = 768):
        self.width = width
        self.height = height

    def generate(self, prompt: str, book_id: int, page: int) -> str | None:
        url = (
            f"{POLLINATIONS_URL}/{urllib.parse.quote(prompt[:400])}"
            f"?width={self.width}&height={self.height}&nologo=true&seed={book_id * 1000 + page}"
        )
        token = os.getenv("POLLINATIONS_TOKEN", "")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            r = httpx.get(url, timeout=90, follow_redirects=True, headers=headers)
            r.raise_for_status()
            if not r.headers.get("content-type", "").startswith("image/"):
                return None
        except httpx.HTTPError:
            # A missing illustration must never fail the book — the generator
            # records the reason and the page still renders its text.
            return None

        dest = STATIC_DIR / "images" / str(book_id)
        dest.mkdir(parents=True, exist_ok=True)
        (dest / f"{page}.jpg").write_bytes(r.content)
        return f"/static/images/{book_id}/{page}.jpg"
