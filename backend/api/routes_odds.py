from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import httpx
from utils.config import ODDS_API_KEY
import crud.odds as crud_odds
from database.connection import get_db
from services.odds_service import get_odds_data

router = APIRouter(prefix = "/odds", tags = ["Odds"])

BASE_URL = "https://api.the-odds-api.com/v4/sports"



@router.get("/{sport}/odds")
async def get_odds(sport: str, db: Session = Depends(get_db)):
    return await get_odds_data(db,sport)