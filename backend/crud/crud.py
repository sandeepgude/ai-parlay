from sqlalchemy.orm import Session
from models.bet import Bet
from schemas.schemas import BetCreate

def get_bets(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Bet).offset(skip).limit(limit).all()

def create_bet(db: Session, bet: BetCreate):
    db_bet = Bet(
        team_name=bet.team_name,
        odds=bet.odds,
        wager_amount=bet.wager_amount
    )
    db.add(db_bet)
    db.commit()
    db.refresh(db_bet)
    return db_bet
