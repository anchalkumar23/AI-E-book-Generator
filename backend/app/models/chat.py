from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Chat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(foreign_key="chat.id", index=True)
    role: str                       # 'user' | 'assistant'
    content: str
    book_id: Optional[int] = Field(default=None, foreign_key="book.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
