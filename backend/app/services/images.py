import os
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
        "?width=768&height=1024&nologo=true&model=turbo"
    )


def download_image(prompt: str, style_prefix: str, book_id: int, page_num: int) -> str | None:
    """Fetches image from Pollinations, saves to disk, returns the local served URL."""
    url = _pollinations_url(prompt, style_prefix)

    img_dir = STATIC_DIR / str(book_id)
    img_dir.mkdir(parents=True, exist_ok=True)
    img_path = img_dir / f"page_{page_num}.jpg"

    try:
        with httpx.stream("GET", url, timeout=90, follow_redirects=True) as r:
            r.raise_for_status()
            with open(img_path, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        return f"{BACKEND_URL}/static/images/{book_id}/page_{page_num}.jpg"
    except Exception:
        return None
