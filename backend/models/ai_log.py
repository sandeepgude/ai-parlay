from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from database.connection import Base

class AILog(Base):
    __tablename__ = "ai_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_message = Column(Text)
    detected_sport = Column(String(50))
    grok_context = Column(Text)
    ai_prompt = Column(Text)
    ai_response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)