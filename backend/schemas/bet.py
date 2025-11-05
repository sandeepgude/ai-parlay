from pydantic import BaseModel

class BetBase(BaseModel):
    team_name: str
    odds: float
    wager_amount: float

class BetCreate(BetBase):
    pass  # user_id comes from auth, not the body

class Bet(BetBase):
    id: int
    user_id: int

    model_config = {"from_attributes": True}
