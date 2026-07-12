"""
Structured book generation pipeline:
  1. Research (optional, DuckDuckGo multi-source)
  2. Blueprint  — outline, characters, style guide, chapter breakdown
  3. Chapters   — one LLM call per chapter → pages with text + illustration prompts
  4. Images     — download from Pollinations per page (notifies WS after each)
  5. Finalise
"""
import json
from datetime import datetime
from typing import Callable
from sqlmodel import Session
from ..database import engine
from ..models.book import Book, BookStatus
from .search import research
from .llm import generate_json, stream_json
from .images import download_image, REAL_PERSON_MESSAGE


class _TextExtractor:
    """Emit only prose content from 'text' JSON fields during streaming."""
    _ESC = {'n': '\n', 't': '\t', 'r': '\r', '"': '"', '\\': '\\'}

    def __init__(self, notify: Callable[[str], None]):
        self._notify = notify
        self._buf = ""
        self._in_value = False
        self._esc = False

    def feed(self, raw: str) -> None:
        for ch in raw:
            if self._in_value:
                if self._esc:
                    self._esc = False
                    self._notify(self._ESC.get(ch, ch))
                elif ch == '\\':
                    self._esc = True
                elif ch == '"':
                    self._in_value = False
                    self._buf = ""
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


# ── Prompts ─────────────────────────────────────────────────────────────────

_BLUEPRINT_PROMPT = """\
You are a senior book editor and author. Create a complete book blueprint.

Title: "{title}"
Topic / premise: {prompt}
Book type: {book_type}
Total pages: {page_count}
Illustration style: {illustration_style}
{writing_style_hint}
{research_block}

Return ONLY valid JSON:
{{
  "writing_style": "detailed description of prose style and voice",
  "tone": "tone and emotional register",
  "target_audience": "who this book is written for",
  "visual_style": "one concise sentence describing the consistent illustration aesthetic",
  "color_palette": "dominant colours for illustrations (e.g. 'warm earth tones, golden highlights')",
  "characters": [
    {{
      "name": "Character Name",
      "role": "protagonist / antagonist / supporting",
      "description": "personality and backstory",
      "visual": "detailed physical appearance for illustration consistency"
    }}
  ],
  "chapters": [
    {{
      "number": 1,
      "title": "Chapter Title",
      "summary": "what happens in this chapter",
      "page_count": 4,
      "key_events": ["event 1", "event 2"]
    }}
  ]
}}

Rules:
- The sum of all chapter page_counts MUST equal {page_count}.
- Writing style and visual style must be internally consistent.
- For children's books: simple vocabulary, short chapters, 2-4 pages each.
- For guides/tutorials/educational: structured chapters, 4-8 pages each.
- For stories: narrative arc with rising action, climax, resolution.
"""

_CHAPTER_PROMPT = """\
You are writing Chapter {chapter_number}: "{chapter_title}" of the book "{book_title}".

Chapter summary: {chapter_summary}
Key events to cover: {key_events}

Book context (maintain consistency throughout):
- Writing style: {writing_style}
- Tone: {tone}
- Target audience: {target_audience}
- Visual style: {visual_style}
- Color palette: {color_palette}
- Characters: {characters_json}

Generate exactly {page_count} pages for this chapter. Return ONLY valid JSON:
{{
  "pages": [
    {{
      "page_number": {start_page},
      "heading": "page heading or scene title",
      "text": "substantial page body — see length rules below",
      "illustration": {{
        "scene": "what is happening in this specific moment",
        "characters_present": "which characters appear and what they are doing",
        "environment": "location, setting, time of day",
        "mood": "emotional atmosphere",
        "lighting": "lighting quality and direction",
        "composition": "camera angle, framing, focal point",
        "style_note": "any style deviation for this page only"
      }},
      "requires_real_person": false
    }}
  ]
}}

Text length rules (non-negotiable):
- children's book: 3-4 short paragraphs per page, simple words
- story: 4-6 paragraphs of vivid narrative prose per page
- guide / tutorial / educational: 5-8 paragraphs with explanations, examples, takeaways
- custom: 4-6 rich paragraphs
Use \\n between paragraphs. Never write a single paragraph per page.

Consistency rules:
- Match the writing style exactly as described above.
- Characters must look and behave consistently with their descriptions.
- Visual style must match throughout — do not invent new styles.
- illustration.scene must describe THIS page's unique moment, not a generic scene.
"""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _save(book: Book, session: Session, **kwargs):
    for k, v in kwargs.items():
        setattr(book, k, v)
    book.last_modified = datetime.utcnow()
    session.commit()


def _build_image_prompt(illus: dict, visual_style: str, color_palette: str) -> str:
    parts = [
        visual_style,
        illus.get("scene", ""),
        illus.get("environment", ""),
        f"{illus.get('mood', '')} mood",
        f"{illus.get('lighting', '')} lighting",
        illus.get("composition", ""),
        f"color palette: {color_palette}",
    ]
    return ", ".join(p for p in parts if p.strip())


# ── Entry point ───────────────────────────────────────────────────────────────

def run_generation(book_id: int, notify: Callable | None = None) -> None:
    _notify = notify or (lambda _: None)
    with Session(engine) as session:
        book = session.get(Book, book_id)
        if not book:
            return
        try:
            _generate(book, session, _notify)
        except Exception as e:
            _save(book, session,
                  status=BookStatus.error,
                  error_message=str(e)[:500],
                  progress_label="Generation failed")
            _notify({"type": "error", "message": str(e)[:500]})


def _generate(book: Book, session: Session, notify: Callable) -> None:
    sources: list[dict] = []

    # ── Phase 1: Research ────────────────────────────────────────────────────
    research_block = ""
    if book.use_research:
        _save(book, session, progress=5, progress_label="Researching topic…")
        notify({"type": "progress", "progress": 5, "label": "Researching topic…"})
        facts, sources = research(f"{book.title} {book.prompt}")
        research_block = f"\nResearch findings (incorporate naturally):\n{facts}\n"

    # ── Phase 2: Blueprint ────────────────────────────────────────────────────
    _save(book, session, progress=10, progress_label="Creating book outline…")
    notify({"type": "progress", "progress": 10, "label": "Creating book outline…"})

    writing_style_hint = (
        f"Writing style requirement: Write this entire book in a {book.writing_style} style."
        if book.writing_style else ""
    )

    blueprint = generate_json(_BLUEPRINT_PROMPT.format(
        title=book.title,
        prompt=book.prompt,
        book_type=book.book_type,
        page_count=book.page_count,
        illustration_style=book.illustration_style,
        writing_style_hint=writing_style_hint,
        research_block=research_block,
    ))

    _save(book, session,
          progress=20,
          progress_label="Outline ready — writing chapters…",
          outline=json.dumps(blueprint))
    notify({"type": "progress", "progress": 20, "label": "Outline ready — writing chapters…"})

    visual_style    = blueprint.get("visual_style",    book.illustration_style)
    color_palette   = blueprint.get("color_palette",   "varied")
    writing_style   = blueprint.get("writing_style",   "engaging and clear")
    tone            = blueprint.get("tone",            "appropriate for the genre")
    target_audience = blueprint.get("target_audience", "general readers")
    characters      = blueprint.get("characters",      [])
    chapters        = blueprint.get("chapters",        [])

    if not chapters:
        raise ValueError("Blueprint returned no chapters.")

    # ── Phase 3: Write chapters ───────────────────────────────────────────────
    all_pages: list[dict] = []
    page_cursor = 1

    for ci, chapter in enumerate(chapters):
        label = f"Writing chapter {ci + 1}/{len(chapters)}: {chapter.get('title', '')}…"
        chapter_progress = 20 + round((ci / len(chapters)) * 35)
        _save(book, session, progress=chapter_progress, progress_label=label)
        notify({"type": "progress", "progress": chapter_progress, "label": label})

        extractor = _TextExtractor(lambda tok: notify({"type": "token", "token": tok}))
        chapter_data = stream_json(_CHAPTER_PROMPT.format(
            chapter_number=chapter.get("number", ci + 1),
            chapter_title=chapter.get("title", f"Chapter {ci + 1}"),
            book_title=book.title,
            chapter_summary=chapter.get("summary", ""),
            key_events=", ".join(chapter.get("key_events", [])),
            writing_style=writing_style,
            tone=tone,
            target_audience=target_audience,
            visual_style=visual_style,
            color_palette=color_palette,
            characters_json=json.dumps(characters),
            page_count=chapter.get("page_count", 4),
            start_page=page_cursor,
        ), extractor.feed)

        for p in chapter_data.get("pages", []):
            p["chapter"] = chapter.get("title", "")
            all_pages.append(p)
            page_cursor += 1

    # ── Phase 4: Generate illustrations ──────────────────────────────────────
    total_pages = len(all_pages)
    result_pages: list[dict] = []

    for i, p in enumerate(all_pages):
        img_label    = f"Generating illustrations ({i + 1}/{total_pages})…"
        img_progress = 55 + round(((i + 1) / max(total_pages, 1)) * 40)

        illus = p.get("illustration", {})

        if p.get("requires_real_person"):
            img_url     = None
            img_message = REAL_PERSON_MESSAGE
        else:
            img_prompt = _build_image_prompt(illus, visual_style, color_palette)
            img_url    = download_image(img_prompt, "", book.id, p.get("page_number", i + 1))
            img_message = None if img_url else "Image could not be generated."

        page_result = {
            "page_number":   p.get("page_number", i + 1),
            "chapter":       p.get("chapter", ""),
            "heading":       p.get("heading", ""),
            "text":          p.get("text", ""),
            "image_url":     img_url,
            "image_message": img_message,
            "illustration":  illus,
        }
        result_pages.append(page_result)

        # Save partial content after each page so reader can reconnect mid-generation
        partial = json.dumps({
            "visual_style":  visual_style,
            "color_palette": color_palette,
            "characters":    characters,
            "pages":         result_pages,
            "sources":       [],
            "generating":    True,
        })
        _save(book, session, progress=img_progress, progress_label=img_label, content=partial)
        notify({"type": "progress", "progress": img_progress, "label": img_label})
        notify({"type": "page",     "page": page_result})

    # ── Phase 5: Finalise ─────────────────────────────────────────────────────
    content = json.dumps({
        "visual_style":  visual_style,
        "color_palette": color_palette,
        "characters":    characters,
        "pages":         result_pages,
        "sources":       sources,
        "generating":    False,
    })

    _save(book, session,
          content=content,
          status=BookStatus.done,
          progress=100,
          progress_label="Done")
    notify({"type": "done", "content": content})
