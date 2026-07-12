import asyncio
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select
from ..database import get_session
from ..models.book import Book
from ..schemas.book import BookCreate, BookUpdate
from ..services.generator import run_generation
from ..services.ws_manager import manager as ws_manager

router = APIRouter()


@router.get("/", response_model=List[Book])
def list_books(session: Session = Depends(get_session)):
    return session.exec(select(Book).order_by(Book.created_at.desc())).all()


@router.post("/", response_model=Book, status_code=201)
async def create_book(data: BookCreate, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    book = Book(**data.model_dump())
    session.add(book)
    session.commit()
    session.refresh(book)
    loop = asyncio.get_running_loop()

    def notify(event: dict):
        ws_manager.publish(book.id, event, loop)

    background_tasks.add_task(run_generation, book.id, notify)
    return book


@router.websocket("/{book_id}/ws")
async def book_ws(book_id: int, websocket: WebSocket, session: Session = Depends(get_session)):
    await websocket.accept()
    book = session.get(Book, book_id)
    if not book:
        await websocket.close(code=4004)
        return

    # Send current snapshot immediately so the client can render existing state
    await websocket.send_json({
        "type":     "state",
        "progress": book.progress,
        "label":    book.progress_label,
        "status":   book.status,
        "content":  book.content,
    })

    if book.status != "generating":
        await websocket.close()
        return

    q = ws_manager.subscribe(book_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(q.get(), timeout=120)
                await websocket.send_json(data)
                if data.get("type") in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.unsubscribe(book_id, q)


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
