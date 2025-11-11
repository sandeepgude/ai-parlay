from sqlalchemy.orm import Session
from models.game_odds import GameOdds
from datetime import datetime, timedelta

def save_odds(db: Session, sport: str, home_team: str, away_team: str, bookmaker: str, market: str, odds_data: dict):
    entry = GameOdds(
        sport=sport,
        home_team=home_team,
        away_team=away_team,
        bookmaker=bookmaker,
        market=market,
        odds_data=odds_data,
        fetched_at=datetime.utcnow()
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def get_recent_odds(db: Session, sport: str, max_age_hours: int = 6):
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    return db.query(GameOdds).filter(GameOdds.sport == sport, GameOdds.fetched_at >= cutoff).all()
