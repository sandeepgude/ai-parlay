from fastapi import APIRouter
from typing import List

router = APIRouter(prefix="/bets", tags = ["Bets"])

@router.get("/")
def get_bets():
    return {"message": "List of all bets will appear here"}

@router.post("/")
def add_bet():
    return {"message":"New bet added successfully!"}

