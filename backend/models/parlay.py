from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey
from datetime import datetime
from database.connection import Base

class Parlay(Base):
    __tablename__ = "parlays"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # optional
    sport = Column(String, index=True)
    legs = Column(JSON)                     # [{team, market, odds, reason}]
    total_odds = Column(Float)
    potential_payout = Column(Float)
    ai_response = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
