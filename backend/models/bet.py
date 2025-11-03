from sqlalchemy import Column, Integer, String, Float
from database.connection import Base

class Bet(Base):
    __tablename__ = "bets"

    id = Column(Integer, primary_key = True, index = True)
    team_name = Column(String, index=True)
    odds = Column(Float)
    wager = Column(Float)
    outcome = Column(String)
    
