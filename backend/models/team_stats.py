from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Index
from database.connection import Base


class TeamStats(Base):
    __tablename__ = "team_stats"

    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String, index=True, nullable=False)
    team = Column(String, index=True, nullable=False)
    stats = Column(JSON, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)


# Common lookup index for sport + team
Index("idx_team_stats_sport_team", TeamStats.sport, TeamStats.team)
