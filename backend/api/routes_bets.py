from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
import crud.crud as crud
from schemas.bet import Bet, BetCreate
from models.user import User
from utils.dependencies import get_current_user

router = APIRouter(prefix="/bets", tags=["Bets"])

@router.get("/", response_model=List[Bet])
def read_bets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.get_bets(db=db, user_id=current_user.id, skip=skip, limit=limit)

@router.post("/", response_model=Bet, status_code=status.HTTP_201_CREATED)
def create_new_bet(
    bet: BetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.create_bet(db=db, bet=bet, user_id=current_user.id)
