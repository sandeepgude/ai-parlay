from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.connection import get_db

from crud.parlay import (
    get_parlays_by_user,
    delete_parlay_by_id
)

from models.parlay import Parlay
from utils.response import success_response

router = APIRouter(prefix="/parlays", tags=["Parlays"])


# ============================
# GET ALL PARLAYS (admin view)
# ============================
@router.get("/all")
def get_parlays(db: Session = Depends(get_db)):
    parlays = db.query(Parlay).order_by(Parlay.id.desc()).all()

    return success_response([
        {
            "id": p.id,
            "user_id": p.user_id,
            "sport": p.sport,
            "legs": p.legs,
            "total_odds": p.total_odds,
            "potential_payout": p.potential_payout,
            "ai_response": p.ai_response,
            "created_at": p.created_at.isoformat()
        }
        for p in parlays
    ])


# ============================
# GET ALL PARLAYS FOR A USER
# ============================
@router.get("/{user_id}")
def get_user_parlays(user_id: int, db: Session = Depends(get_db)):
    parlays = get_parlays_by_user(db, user_id)
    return success_response(parlays)


# ============================
# DELETE ONE PARLAY BY ID
# ============================
@router.delete("/{id}")
def delete_parlay(id: int, db: Session = Depends(get_db)):
    result = delete_parlay_by_id(db, id)

    if result:
        return success_response({"deleted": True})
    else:
        return success_response({"deleted": False})


# ============================
# SAVE A NEW PARLAY
# ============================
@router.post("/save")
def save_parlay(data: dict, db: Session = Depends(get_db)):

    parlay = Parlay(
        user_id=data.get("user_id"),
        sport=data.get("sport"),
        legs=data.get("legs"),
        total_odds=data.get("total_odds"),
        potential_payout=data.get("potential_payout"),
        ai_response=data.get("ai_response"),
    )

    db.add(parlay)
    db.commit()
    db.refresh(parlay)

    return success_response({
        "id": parlay.id,
        "created_at": parlay.created_at
    })
