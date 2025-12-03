from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, UniqueConstraint
from datetime import datetime
from database.connection import Base


class TeamMarket(Base):
    __tablename__ = "team_markets"
    __table_args__ = (
        UniqueConstraint("game_id", "bookmaker", "market", name="uq_team_market"),
    )

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    sport = Column(String, index=True, nullable=False)
    bookmaker = Column(String, nullable=False)
    market = Column(String, nullable=False)  # h2h, spreads, totals
    odds_data = Column(JSON, nullable=False)
    commence_time = Column(String, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)
