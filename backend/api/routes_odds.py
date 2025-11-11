from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import httpx
from utils.config import ODDS_API_KEY
import crud.odds as crud_odds
from database.connection import get_db


router = APIRouter(prefix = "/odds", tags = ["Odds"])

BASE_URL = "https://api.the-odds-api.com/v4/sports"

SPORT_MAP = {
    "nfl": "americanfootball_nfl",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "soccer": "soccer_usa_mls"
}


@router.get("/{sport}/odds")
async def get_odds(sport: str, db: Session = Depends(get_db)):

    cached = crud_odds.get_recent_odds(db,sport)
    if cached:
        return {"source": "cache", "data": cached}

    if not ODDS_API_KEY:
        raise HTTPException(status_code=500, detail="Missing API Key")
    sport_key = SPORT_MAP.get(sport.lower())
    url = f"{BASE_URL}/{sport_key}/odds/?apiKey={ODDS_API_KEY}&regions=us&markets=h2h,spreads,totals"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code = response.status_code, detail=response.text)
        odds_data =  response.json()

    for game in odds_data:
        home = game.get("home_team")
        away = game.get("away_team")
        for bookmaker in game.get("bookmakers", []):
            title = bookmaker.get("title")
            for market in bookmaker.get("markets", []):
                crud_odds.save_odds(
                    db,
                    sport,
                    home,
                    away,
                    title,
                    market.get("key"),
                    market.get("outcomes"),
                )

    return {"source": "api", "data": odds_data}
    