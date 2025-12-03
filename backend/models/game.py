from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from datetime import datetime
from database.connection import Base


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (UniqueConstraint("sport", "event_id", name="uq_game_sport_event"),)

    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String, index=True, nullable=False)
    event_id = Column(String, nullable=False)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    commence_time = Column(String, nullable=True)
    source = Column(String, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)
