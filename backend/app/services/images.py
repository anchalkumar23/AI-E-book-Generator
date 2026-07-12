import os
import time
import httpx
from pathlib import Path
from urllib.parse import quote

REAL_PERSON_MESSAGE = (
    "Real person image required. "
    "Please provide a licensed image or add it manually."
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
STATIC_DIR  = Path(__file__).parent.parent.parent / "static" / "images"


def _pollinations_url(prompt: str, style_prefix: str) -> str:
    full = f"{style_prefix}, {prompt}" if style_prefix else prompt
    encoded = quote(full[:400])
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        "?width=512&height=680&nologo=true&model=turbo"
    )


def download_image(prompt: str, style_prefix: str, book_id: int, page_num: int) -> str | None:
    """Fetches image from Pollinations with retry/backoff on rate limits, saves to disk."""
    url = _pollinations_url(prompt, style_prefix)

    img_dir = STATIC_DIR / str(book_id)
    img_dir.mkdir(parents=True, exist_ok=True)
    img_path = img_dir / f"page_{page_num}.jpg"

    for attempt in range(5):
        try:
            with httpx.stream("GET", url, timeout=120, follow_redirects=True) as r:
                if r.status_code == 429 or r.status_code >= 500:
                    raise httpx.HTTPError(f"retryable {r.status_code}")
                r.raise_for_status()
                with open(img_path, "wb") as f:
                    for chunk in r.iter_bytes(chunk_size=8192):
                        f.write(chunk)
            return f"{BACKEND_URL}/static/images/{book_id}/page_{page_num}.jpg"
        except Exception:
            if attempt < 4:
                time.sleep(4 * (attempt + 1))  # 4, 8, 12, 16s — waits out rate limits
    return None
