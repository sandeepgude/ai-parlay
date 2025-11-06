from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List
from database.connection import get_db
from models.user import User
from schemas.bet import Bet, BetCreate
from utils.dependencies import get_current_user
from utils.response import success_response, error_response
import crud.crud as crud

router = APIRouter(prefix="/bets", tags=["Bets"])

@router.get("/", response_model=None)
def read_bets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        bets = crud.get_bets(db=db, user_id=current_user.id, skip=skip, limit=limit)
        return success_response("Fetched bets successfully", bets)
    except Exception as e:
        return error_response(f"Error fetching bets: {e}")

@router.post("/", response_model=None, status_code=status.HTTP_201_CREATED)
def create_new_bet(
    bet: BetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        new_bet = crud.create_bet(db=db, bet=bet, user_id=current_user.id)
        return success_response("Bet created successfully", new_bet)
    except Exception as e:
        return error_response(f"Error creating bet: {e}")
