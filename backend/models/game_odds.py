from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from database.connection import Base


class GameOdds(Base):
    __tablename__ = "game_odds"

    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String, index=True)
    home_team = Column(String)
    away_team = Column(String)
    bookmaker = Column(String)
    market = Column(String)
    odds_data = Column(JSON)
    fetched_at = Column(DateTime, default=datetime.utcnow)
