from sqlalchemy.orm import Session
from models.bet import Bet
from schemas.bet import BetCreate

def get_bets(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return (db.query(Bet)
            .filter(Bet.user_id == user_id)
            .offset(skip).limit(limit).all())

def create_bet(db: Session, bet: BetCreate, user_id: int):
    db_bet = Bet(
        team_name=bet.team_name,
        odds=bet.odds,
        wager_amount=bet.wager_amount,
        user_id=user_id,
    )
    db.add(db_bet)
    db.commit()
    db.refresh(db_bet)
    return db_bet

