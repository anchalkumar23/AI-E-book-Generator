from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models.setting import Setting
from ..services.config import DEFAULTS, setting

router = APIRouter()


@router.get("/")
def get_settings(session: Session = Depends(get_session)) -> dict:
    """Returns effective values (DB -> env -> default), not raw defaults.

    Returning raw defaults would show an empty key whenever one came from the
    environment — and saving that form would write the blank into the DB, where
    it outranks the env var and silently breaks generation.
    """
    return {key: setting(session, key) for key in DEFAULTS}


@router.put("/")
def update_settings(data: dict, session: Session = Depends(get_session)) -> dict:
    for key, value in data.items():
        if key not in DEFAULTS:
            continue
        row = session.get(Setting, key)
        if row:
            row.value = str(value)
        else:
            session.add(Setting(key=key, value=str(value)))
    session.commit()
    return get_settings(session)
