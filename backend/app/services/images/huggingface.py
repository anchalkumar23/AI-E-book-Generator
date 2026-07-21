"""Illustrations via Hugging Face Inference (FLUX.1-schnell).

Free tier: create a token at huggingface.co/settings/tokens (no card) and set
HF_TOKEN. Without a token this returns None immediately rather than burning a
request per page.

Serverless models sleep when idle and answer the first call with 503 plus an
estimated load time, so one retry is expected on a cold start — not a failure.

Images are stored under static/ rather than hotlinked so a book reads offline.
The stored path is engine-relative (`/static/…`): the engine's port changes each
launch, so an absolute URL would break on the next start.
"""
import os
import time
from pathlib import Path

import httpx

from .base import ImageProvider

# SD3-medium, not FLUX: Hugging Face deprecated FLUX.1-schnell on the free
# hf-inference provider (410 "no longer supported"), moving it to paid partners.
# At time of writing this is the only text-to-image model the free tier serves,
# so it is worth re-checking if images start failing:
#   GET /api/models?pipeline_tag=text-to-image&inference_provider=hf-inference
HF_MODEL = os.getenv("HF_MODEL", "stabilityai/stable-diffusion-3-medium-diffusers")
HF_URL = os.getenv(
    "HF_API_URL", f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"
)
STATIC_DIR = Path(__file__).resolve().parents[3] / "static"


class HuggingFaceProvider(ImageProvider):
    def __init__(self, token: str | None = None):
        # `is None`, not `or`: an explicit "" means "nothing configured" and must
        # not fall back to the environment. The generator passes the already
        # resolved setting (DB -> env -> ""), so re-reading env would ignore it.
        self.token = os.getenv("HF_TOKEN", "") if token is None else token

    def generate(self, prompt: str, book_id: int, page: int) -> str | None:
        if not self.token:
            return None

        headers = {"Authorization": f"Bearer {self.token}"}
        body = {"inputs": prompt[:800]}

        for attempt in range(2):
            try:
                r = httpx.post(HF_URL, json=body, headers=headers, timeout=120)
            except httpx.HTTPError:
                return None  # a missing illustration must never fail the book

            if r.headers.get("content-type", "").startswith("image/"):
                dest = STATIC_DIR / "images" / str(book_id)
                dest.mkdir(parents=True, exist_ok=True)
                (dest / f"{page}.jpg").write_bytes(r.content)
                return f"/static/images/{book_id}/{page}.jpg"

            # 503 = model waking up. Wait the time HF suggests, then retry once.
            if r.status_code == 503 and attempt == 0:
                wait = 20
                try:
                    wait = min(float(r.json().get("estimated_time", wait)), 60)
                except Exception:
                    pass
                time.sleep(wait)
                continue

            return None

        return None
