"""
Daily ESPN scraper for AI-Parlay.

Usage examples:
  python -m scrapper.main --sport nba --sport nfl          # today (Mountain)
  python -m scrapper.main --sport nba --date 2024-12-01    # specific date
"""

from __future__ import annotations

import argparse
import datetime as dt
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

import httpx

import crud.odds as crud_odds
from database.connection import SessionLocal

MOUNTAIN_TZ = ZoneInfo("America/Denver")

SCOREBOARD_URLS: Dict[str, str] = {
    "nba": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    "nfl": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
}

HEADERS = {"User-Agent": "AI-Parlay-Scraper/1.0"}


def _today_mt_iso() -> str:
    """Today in Mountain Time (ISO date)."""
    return dt.datetime.now(MOUNTAIN_TZ).date().isoformat()


def fetch_scoreboard(sport: str, date_iso: str | None) -> Dict:
    """
    Fetch ESPN scoreboard JSON for a sport and date.
    Tries the requested date, then no date, then previous day (MT) to avoid 404s on off-days.
    """
    url = SCOREBOARD_URLS[sport]
    candidates = []
    if date_iso:
        candidates.append({"dates": date_iso})
    else:
        candidates.append({"dates": _today_mt_iso()})
    candidates.append({})  # ESPN default "current"

    # previous day fallback
    try:
        base_date = dt.date.fromisoformat((date_iso or _today_mt_iso()))
        candidates.append({"dates": (base_date - dt.timedelta(days=1)).isoformat()})
    except Exception:
        pass

    for params in candidates:
        try:
            resp = httpx.get(url, params=params, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                continue
            raise
    return {}


def _normalize_markets(comp: Dict, commence_time: str, provider: str) -> List[Dict]:
    """Extract h2h/spreads/totals odds from a competition block."""
    markets: List[Dict] = []
    home_odds = comp.get("homeTeamOdds") or {}
    away_odds = comp.get("awayTeamOdds") or {}

    # Moneyline
    ml_items = []
    if home_odds.get("moneyLine") is not None:
        ml_items.append({"name": comp.get("home"), "price": home_odds.get("moneyLine")})
    if away_odds.get("moneyLine") is not None:
        ml_items.append({"name": comp.get("away"), "price": away_odds.get("moneyLine")})
    if ml_items:
        markets.append({"market": "h2h", "odds": ml_items, "commence_time": commence_time, "bookmaker": provider})

    # Spreads
    spread_value = comp.get("spread")
    if spread_value is not None:
        markets.append(
            {
                "market": "spreads",
                "odds": [
                    {"name": comp.get("home"), "price": home_odds.get("spreadOdds"), "point": spread_value},
                    {"name": comp.get("away"), "price": away_odds.get("spreadOdds"), "point": -spread_value},
                ],
                "commence_time": commence_time,
                "bookmaker": provider,
            }
        )

    # Totals
    ou_value = comp.get("overUnder")
    if ou_value is not None:
        over_price = comp.get("overOdds") or home_odds.get("overOdds")
        under_price = comp.get("underOdds") or away_odds.get("underOdds")
        odds_items = []
        if over_price is not None:
            odds_items.append({"name": "Over", "price": over_price, "point": ou_value})
        if under_price is not None:
            odds_items.append({"name": "Under", "price": under_price, "point": ou_value})
        if odds_items:
            markets.append(
                {"market": "totals", "odds": odds_items, "commence_time": commence_time, "bookmaker": provider}
            )

    return markets


def _parse_event(event: Dict, sport: str) -> Tuple[Dict, List[Dict]]:
    """
    Return (game_info, markets) for a single ESPN event.
    game_info: dict with sport, event_id, home_team, away_team, commence_time
    markets: list of dicts {market, odds, commence_time, bookmaker}
    """
    competitions = event.get("competitions") or []
    if not competitions:
        return {}, []

    comp = competitions[0]
    competitors = comp.get("competitors", [])
    home = next((c.get("team", {}).get("displayName") for c in competitors if c.get("homeAway") == "home"), None)
    away = next((c.get("team", {}).get("displayName") for c in competitors if c.get("homeAway") == "away"), None)
    if not home or not away:
        return {}, []

    commence_time = comp.get("date")
    event_id = str(event.get("id") or f"{home}-{away}-{commence_time}")

    odds_list = []
    for odds in comp.get("odds") or []:
        provider = odds.get("provider", {}).get("name") or "ESPN"
        comp_block = {
            "home": home,
            "away": away,
            "homeTeamOdds": odds.get("homeTeamOdds") or {},
            "awayTeamOdds": odds.get("awayTeamOdds") or {},
            "spread": odds.get("spread"),
            "overUnder": odds.get("overUnder"),
            "overOdds": odds.get("overOdds"),
            "underOdds": odds.get("underOdds"),
        }
        odds_list.extend(_normalize_markets(comp_block, commence_time, provider))

    game_info = {
        "sport": sport,
        "event_id": event_id,
        "home_team": home,
        "away_team": away,
        "commence_time": commence_time,
        "source": "espn_scraper",
    }
    return game_info, odds_list


def scrape_and_store(db, sport: str, date_iso: str) -> Tuple[int, int]:
    """Fetch ESPN data for a sport/date, upsert games + markets. Returns (games, markets)."""
    data = fetch_scoreboard(sport, date_iso)
    if not data:
        print(f"⚠️ {sport}: no scoreboard data found (date={date_iso}, tried fallbacks).")
        return 0, 0
    events = data.get("events") or []

    games_count = 0
    markets_count = 0

    for event in events:
        game_info, markets = _parse_event(event, sport)
        if not game_info:
            continue

        game_row = crud_odds.upsert_game(
            db=db,
            sport=game_info["sport"],
            event_id=game_info["event_id"],
            home_team=game_info["home_team"],
            away_team=game_info["away_team"],
            commence_time=game_info["commence_time"],
            source=game_info["source"],
        )
        games_count += 1

        for market in markets:
            crud_odds.upsert_team_market(
                db=db,
                game_id=game_row.id,
                sport=sport,
                bookmaker=market.get("bookmaker") or "ESPN",
                market=market.get("market"),
                odds_data=market.get("odds") or [],
                commence_time=market.get("commence_time"),
            )
            markets_count += 1

    return games_count, markets_count


def main():
    parser = argparse.ArgumentParser(description="Scrape ESPN scoreboards into the database.")
    parser.add_argument(
        "--sport",
        action="append",
        choices=list(SCOREBOARD_URLS.keys()),
        help="Sport(s) to scrape (can repeat). Default: all.",
    )
    parser.add_argument(
        "--date",
        help="ISO date (YYYY-MM-DD) to scrape. Defaults to today in Mountain Time.",
    )
    args = parser.parse_args()

    sports = args.sport or list(SCOREBOARD_URLS.keys())
    date_iso = args.date or _today_mt_iso()

    print(f"📅 Scraping ESPN for {sports} on {date_iso} (Mountain)")

    db = SessionLocal()
    try:
        for sport in sports:
            try:
                games, markets = scrape_and_store(db, sport, date_iso)
                print(f"✅ {sport}: upserted {games} games, {markets} markets")
            except Exception as e:
                print(f"⚠️ {sport}: scrape error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
