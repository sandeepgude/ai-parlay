from pydantic import BaseModel
from typing import Optional

class BetBase(BaseModel):
    team_name: str
    odds: float
    wager_amount: float

class BetCreate(BetBase):
    pass

class Bet(BetBase):
    id: int

    class Config:
        orm_mode = True
