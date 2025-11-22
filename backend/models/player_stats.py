from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Index
from database.connection import Base


class PlayerStats(Base):
    __tablename__ = "player_stats"

    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String, index=True, nullable=False)
    player = Column(String, index=True, nullable=False)
    stats = Column(JSON, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)


# Common lookup index for sport + player
Index("idx_player_stats_sport_player", PlayerStats.sport, PlayerStats.player)
