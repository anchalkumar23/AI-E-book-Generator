from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select
from ..database import get_session
from ..models.book import Book
from ..schemas.book import BookCreate, BookUpdate
from ..services.generator import run_generation

router = APIRouter()


@router.get("/", response_model=List[Book])
def list_books(session: Session = Depends(get_session)):
    return session.exec(select(Book).order_by(Book.created_at.desc())).all()


@router.post("/", response_model=Book, status_code=201)
def create_book(data: BookCreate, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    book = Book(**data.model_dump())
    session.add(book)
    session.commit()
    session.refresh(book)
    background_tasks.add_task(run_generation, book.id)
    return book


@router.get("/{book_id}", response_model=Book)
def get_book(book_id: int, session: Session = Depends(get_session)):
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    return book


@router.patch("/{book_id}", response_model=Book)
def update_book(book_id: int, data: BookUpdate, session: Session = Depends(get_session)):
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(book, k, v)
    session.commit()
    session.refresh(book)
    return book


@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: int, session: Session = Depends(get_session)):
    book = session.get(Book, book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    session.delete(book)
    session.commit()
