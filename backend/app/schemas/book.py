from typing import Optional
from sqlmodel import SQLModel
from ..models.book import BookType


class BookCreate(SQLModel):
    title: str
    prompt: str
    book_type: BookType   = BookType.tutorial
    page_count: int       = 15
    illustration_style: str = "Digital flat"
    cover_hue: int        = 264
    use_research: bool    = True


class BookUpdate(SQLModel):
    title: Optional[str]         = None
    favorite: Optional[bool]     = None
    status: Optional[str]        = None
    progress: Optional[int]      = None
    progress_label: Optional[str] = None
    content: Optional[str]       = None
    outline: Optional[str]       = None
    error_message: Optional[str] = None
