import os, httpx
from sqlalchemy.orm import Session
import crud.odds as crud_odds
from utils.config import ODDS_API_KEY as API_KEY

BASE_URL = "https://api.the-odds-api.com/v4/sports"


SPORT_MAP = {
    "nfl": "americanfootball_nfl",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "soccer": "soccer_usa_mls"
}


async def get_odds_data(db: Session, sport: str):
    """Get odds from cache or live API."""
    cached = crud_odds.get_recent_odds(db, sport)
    if cached:
        return {"source": "cache", "data": cached}

    if not API_KEY:
        raise ValueError("Missing ODDS_API_KEY")
    sports_map = SPORT_MAP.get(sport);
    url = f"{BASE_URL}/{sports_map}/odds/?apiKey={API_KEY}&regions=us&markets=h2h,spreads,totals"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        res.raise_for_status()
        odds_data = res.json()

    # save to DB
    for game in odds_data:
        home = game.get("home_team")
        away = game.get("away_team")
        for bookmaker in game.get("bookmakers", []):
            title = bookmaker.get("title")
            for market in bookmaker.get("markets", []):
                crud_odds.save_odds(
                    db=db,
                    sport=sport,
                    home_team=home,
                    away_team=away,
                    bookmaker=title,
                    market=market.get("key"),
                    odds_data=market.get("outcomes"),
                )

    return {"source": "api", "data": odds_data}
