from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models.chat import Chat, Message

router = APIRouter()


@router.post("/", response_model=Chat, status_code=201)
def create_chat(data: dict, session: Session = Depends(get_session)):
    chat = Chat(title=data.get("title", "New chat"))
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat


@router.get("/", response_model=list[Chat])
def list_chats(session: Session = Depends(get_session)):
    return session.exec(select(Chat).order_by(Chat.created_at.desc())).all()


@router.delete("/{chat_id}", status_code=204)
def delete_chat(chat_id: int, session: Session = Depends(get_session)):
    chat = session.get(Chat, chat_id)
    if not chat:
        raise HTTPException(404, "chat not found")
    for m in session.exec(select(Message).where(Message.chat_id == chat_id)).all():
        session.delete(m)
    session.delete(chat)
    session.commit()


@router.post("/{chat_id}/messages", response_model=Message, status_code=201)
def add_message(chat_id: int, data: dict, session: Session = Depends(get_session)):
    if not session.get(Chat, chat_id):
        raise HTTPException(404, "chat not found")
    msg = Message(
        chat_id=chat_id,
        role=data["role"],
        content=data["content"],
        book_id=data.get("book_id"),
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg


@router.get("/{chat_id}/messages", response_model=list[Message])
def list_messages(chat_id: int, session: Session = Depends(get_session)):
    return session.exec(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
    ).all()
