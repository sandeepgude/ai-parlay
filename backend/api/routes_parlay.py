from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.connection import get_db
from crud.parlay import get_parlays_by_user, delete_parlays_by_user

router = APIRouter(prefix="/parlays", tags=["Parlays"])

@router.get("/{user_id}")
def get_user_parlays(user_id: int, db: Session = Depends(get_db)):
    parlays = get_parlays_by_user(db, user_id)
    return {"data": parlays}

@router.delete("/parlays/{id}")
def delete_parlay(id: int, db: Session = Depends(get_db)):
    return delete_parlays_by_user(db,id)
