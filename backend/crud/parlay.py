from sqlalchemy.orm import Session
from models.parlay import Parlay

def save_parlay(db: Session, sport: str, legs: list, total_odds: float, payout: float, ai_response: str, user_id: int = None):
    parlay = Parlay(
        sport=sport,
        legs=legs,
        total_odds=total_odds,
        potential_payout=payout,
        ai_response=ai_response,
        user_id=user_id
    )
    db.add(parlay)
    db.commit()
    db.refresh(parlay)
    return parlay

def get_recent_parlays(db: Session, sport: str, limit: int = 10):
    return db.query(Parlay).filter(Parlay.sport == sport).order_by(Parlay.created_at.desc()).limit(limit).all()
