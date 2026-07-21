import os
from pathlib import Path

from sqlmodel import SQLModel, create_engine, Session, text

# Imported for their side effect: SQLModel only creates tables it has seen.
from .models.book import Book              # noqa: F401
from .models.chat import Chat, Message     # noqa: F401
from .models.setting import Setting        # noqa: F401

# The Tauri shell passes the OS app-data directory as argv[1]; engine.py puts it
# in the environment. An installed app must not write next to its executable.
# The fallback keeps pytest and a bare `python -m app.engine` working.
_db_dir = os.getenv("ENGINE_DB_DIR")
if _db_dir:
    Path(_db_dir).mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{Path(_db_dir) / 'pageforge.db'}"
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ebooks.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# New columns added after initial schema — safely ignored if they already exist
_MIGRATIONS = [
    "ALTER TABLE book ADD COLUMN progress_label TEXT DEFAULT ''",
    "ALTER TABLE book ADD COLUMN use_research BOOLEAN DEFAULT 1",
    "ALTER TABLE book ADD COLUMN outline TEXT",
    "ALTER TABLE book ADD COLUMN last_modified DATETIME",
    "ALTER TABLE book ADD COLUMN writing_style TEXT",
]


def create_db():
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        for sql in _MIGRATIONS:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # column already exists


def get_session():
    with Session(engine) as session:
        yield session
