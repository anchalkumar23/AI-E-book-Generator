import os
from sqlmodel import SQLModel, create_engine, Session, text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ebooks.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# New columns added after initial schema — safely ignored if they already exist
_MIGRATIONS = [
    "ALTER TABLE book ADD COLUMN progress_label TEXT DEFAULT ''",
    "ALTER TABLE book ADD COLUMN use_research BOOLEAN DEFAULT 1",
    "ALTER TABLE book ADD COLUMN outline TEXT",
    "ALTER TABLE book ADD COLUMN last_modified DATETIME",
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
