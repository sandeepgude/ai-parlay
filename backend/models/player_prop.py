from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, UniqueConstraint
from datetime import datetime
from database.connection import Base


class PlayerProp(Base):
    __tablename__ = "player_props"
    __table_args__ = (
        UniqueConstraint("game_id", "bookmaker", "player", "stat_type", "side", name="uq_player_prop"),
    )

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    sport = Column(String, index=True, nullable=False)
    bookmaker = Column(String, nullable=False)
    player = Column(String, nullable=False)
    stat_type = Column(String, nullable=False)  # points, assists, rebounds, touchdowns, etc.
    side = Column(String, nullable=True)  # Over/Under or None
    line = Column(Float, nullable=True)
    price = Column(Integer, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)
