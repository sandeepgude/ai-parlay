import httpx
from sqlalchemy.orm import Session
import crud.odds as crud_odds
from utils.config import ODDS_API_KEY as API_KEY

BASE_URL = "https://api.the-odds-api.com/v4/sports"

# Map user-friendly sport → API sport
SPORT_MAP = {
    "nfl": "americanfootball_nfl",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "soccer": "soccer_usa_mls"
}

# Sport-specific supported markets
NBA_MARKETS = (
    "h2h,"
    "spreads,"
    "totals"
    # "player_points,"
    # "player_assists,"
    # "player_rebounds,"
    # "player_threes"
)

NFL_MARKETS = (
    "h2h,"
    "spreads,"
    "totals"
)

DEFAULT_MARKETS = "h2h,spreads,totals"


def get_markets_for_sport(sport: str):
    sport = sport.lower()
    if sport == "nba":
        return NBA_MARKETS
    if sport == "nfl":
        return NFL_MARKETS
    return DEFAULT_MARKETS


# ============================================================================
# ⭐ UNIFIED PARSER — converts raw API format → AI-ready clean structure
# ============================================================================
def parse_game_odds(game):
    home = game.get("home_team")
    away = game.get("away_team")

    parsed = {
        "game_id": f"{home} vs {away}",
        "home_team": home,
        "away_team": away,

        # Core markets
        "moneyline": {},
        "spreads": [],
        "totals": [],

        # Advanced (NBA-only)
        "player_props": []
    }

    for book in game.get("bookmakers", []):
        book_name = book.get("title")

        for market in book.get("markets", []):
            key = market.get("key")
            outcomes = market.get("outcomes", [])

            # MONEYLINE
            if key == "h2h":
                for o in outcomes:
                    parsed["moneyline"][o["name"]] = {
                        "odds": o.get("price"),
                        "book": book_name
                    }

            # SPREADS
            elif key == "spreads":
                for o in outcomes:
                    parsed["spreads"].append({
                        "team": o.get("name"),
                        "line": o.get("point"),
                        "odds": o.get("price"),
                        "book": book_name
                    })

            # TOTALS
            elif key == "totals":
                for o in outcomes:
                    parsed["totals"].append({
                        "type": o.get("name"),
                        "line": o.get("point"),
                        "odds": o.get("price"),
                        "book": book_name
                    })

            # PLAYER PROPS (NBA ONLY)
            elif key.startswith("player_"):
                stat_type = key.replace("player_", "")
                for o in outcomes:
                    parsed["player_props"].append({
                        "player": o.get("name"),
                        "stat": stat_type,
                        "line": o.get("point"),
                        "odds": o.get("price"),
                        "book": book_name
                    })

    return parsed


# ============================================================================
# ⭐ Main Function — Fetch & Parse Odds
# ============================================================================
async def get_odds_data(db: Session, sport: str):
    """
    Fetch odds from cache or API.
    Returns CLEAN, AI-ready list of parsed games.
    """
    # 1️⃣ Return cached data if exists
    cached = crud_odds.get_recent_odds(db, sport)
    if cached:
        return {"source": "cache", "data": cached}

    # 2️⃣ Map sport → API code
    sport_key = SPORT_MAP.get(sport)
    if not sport_key:
        raise ValueError(f"Unsupported sport: {sport}")

    if not API_KEY:
        raise ValueError("Missing ODDS_API_KEY")

    # 3️⃣ Determine valid markets
    markets = get_markets_for_sport(sport)

    # 4️⃣ Build API URL
    url = (
        f"{BASE_URL}/{sport_key}/odds/"
        f"?apiKey={API_KEY}"
        f"&regions=us"
        f"&markets={markets}"
        f"&bookmakers=fanduel"
        f"&oddsFormat=american"
    )


    print(f"📡 Fetching odds for {sport} with markets: {markets}")

    # 5️⃣ Fetch from API
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(url)
            res.raise_for_status()
            odds_data = res.json()
    except httpx.HTTPStatusError as e:
        print(f"⚠️ Odds API error ({e.response.status_code}): {e}")
        return {
            "source": "error",
            "data": [],
            "error": f"odds_api_{e.response.status_code}",
            "detail": str(e),
        }

    # 6️⃣ Save only core markets to DB
    for game in odds_data:
        home = game.get("home_team")
        away = game.get("away_team")

        for bookmaker in game.get("bookmakers", []):
            title = bookmaker.get("title")

            for market in bookmaker.get("markets", []):
                key = market.get("key")

                if key in ["h2h", "spreads", "totals"]:
                    crud_odds.save_odds(
                        db=db,
                        sport=sport,
                        home_team=home,
                        away_team=away,
                        bookmaker=title,
                        market=key,
                        odds_data=market.get("outcomes")
                    )

    # 7️⃣ Convert raw → parsed AI-friendly structure
    parsed_games = [parse_game_odds(g) for g in odds_data]

    return {
        "source": "api",
        "data": parsed_games
    }
