from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class BookStatus(str, Enum):
    generating = "generating"
    done = "done"
    error = "error"


class BookType(str, Enum):
    childrens   = "childrens"
    tutorial    = "tutorial"
    guide       = "guide"
    educational = "educational"
    story       = "story"
    custom      = "custom"


class Book(SQLModel, table=True):
    id: Optional[int]     = Field(default=None, primary_key=True)
    title: str
    prompt: str
    book_type: BookType   = BookType.tutorial
    page_count: int       = 15
    illustration_style: str = "Digital flat"
    status: BookStatus    = BookStatus.generating
    cover_hue: int        = 264
    favorite: bool        = False
    progress: int         = 0
    progress_label: str   = ""
    use_research: bool    = True
    created_at: datetime  = Field(default_factory=datetime.utcnow)
    last_modified: Optional[datetime] = None
    outline: Optional[str]      = None   # JSON book blueprint
    content: Optional[str]      = None   # JSON pages array
    error_message: Optional[str] = None
