from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.connection import get_db
import crud.crud as crud
from schemas.schemas import Bet, BetCreate
from typing import List

router = APIRouter()

@router.get("/bets", response_model=List[Bet])
def read_bets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_bets(db=db, skip=skip, limit=limit)

@router.post("/bets", response_model=Bet)
def create_new_bet(bet: BetCreate, db: Session = Depends(get_db)):
    return crud.create_bet(db=db, bet=bet)
