from fastapi import APIRouter, HTTPException

router = APIRouter()

_credits = {"remaining": 31, "total": 50}


@router.get("/")
def get_credits():
    return _credits


@router.post("/consume")
def consume_credit():
    if _credits["remaining"] <= 0:
        raise HTTPException(400, "No credits remaining")
    _credits["remaining"] -= 1
    return _credits
