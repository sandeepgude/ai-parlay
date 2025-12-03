import asyncio
import datetime as _dt
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

import crud.odds as crud_odds
from utils.config import ODDS_API_KEY as API_KEY

BASE_URL = "https://api.the-odds-api.com/v4/sports"
ESPN_SCOREBOARD_URLS = {
    "nba": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    "nfl": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
}

# Map user-friendly sport → API sport
SPORT_MAP = {
    "nfl": "americanfootball_nfl",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "soccer": "soccer_usa_mls",
}

# Sport-specific supported markets
NBA_MARKETS = "h2h,spreads,totals,player_points,player_assists,player_rebounds,player_threes"
NFL_MARKETS = "h2h,spreads,totals,player_touchdowns,player_rush_yards,player_rec_yards"
DEFAULT_MARKETS = "h2h,spreads,totals"
MAX_CACHE_HOURS = 3
MOUNTAIN_TZ = ZoneInfo("America/Denver")


def get_markets_for_sport(sport: str):
    sport = sport.lower()
    if sport == "nba":
        return NBA_MARKETS
    if sport == "nfl":
        return NFL_MARKETS
    return DEFAULT_MARKETS


def _normalize_market_entry(
    sport: str,
    home: str,
    away: str,
    bookmaker: str,
    market: str,
    odds: List[Dict],
    commence_time: Optional[str] = None,
):
    """Create a consistent market dict for the rest of the pipeline."""
    return {
        "home_team": home,
        "away_team": away,
        "sport": sport,
        "bookmaker": bookmaker,
        "market": market,
        "odds": odds,
        "commence_time": commence_time,
    }


def _dedupe_markets(markets: List[Dict]) -> List[Dict]:
    seen = set()
    unique: List[Dict] = []
    for m in markets:
        key = (
            m.get("home_team"),
            m.get("away_team"),
            m.get("market"),
            m.get("bookmaker"),
            m.get("commence_time"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(m)
    return unique


def _normalize_player_prop_odds_entry(player: str, stat_type: str, side: Optional[str], line, price):
    return {
        "player": player,
        "name": player,
        "side": side,
        "price": price,
        "point": line,
        "stat": stat_type,
    }


def _is_today_commence(commence_time: Optional[str]) -> bool:
    """Return True if commence_time is today in Mountain Time."""
    if not commence_time:
        return False
    try:
        if isinstance(commence_time, str):
            ts = commence_time.replace("Z", "+00:00")
            dt_obj = _dt.datetime.fromisoformat(ts)
        elif isinstance(commence_time, _dt.datetime):
            dt_obj = commence_time
        else:
            return False

        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=_dt.timezone.utc)

        local_dt = dt_obj.astimezone(MOUNTAIN_TZ)
        return local_dt.date() == _dt.datetime.now(MOUNTAIN_TZ).date()
    except Exception:
        return False


# ============================================================================
# ⭐ FanDuel odds via TheOddsAPI (bookmaker filtered to FanDuel)
# ============================================================================
async def _fetch_fanduel_odds(db: Session, sport: str) -> List[Dict]:
    sport_key = SPORT_MAP.get(sport)
    if not sport_key or not API_KEY:
        return []

    markets_out: List[Dict] = []

    # Try core markets first to avoid noisy 422s, then richer set
    market_options = [DEFAULT_MARKETS, get_markets_for_sport(sport)]

    odds_data = None
    last_err = None
    for markets in market_options:
        url = (
            f"{BASE_URL}/{sport_key}/odds/"
            f"?apiKey={API_KEY}"
            f"&regions=us"
            f"&markets={markets}"
            f"&bookmakers=fanduel"
            f"&oddsFormat=american"
        )
        print(f"📡 Fetching FanDuel odds for {sport} with markets: {markets}")
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                res = await client.get(url)
                await asyncio.sleep(2)  # pause between requests to ease rate limits
                res.raise_for_status()
                odds_data = res.json()
                break
        except httpx.HTTPStatusError as e:
            last_err = e
            if e.response.status_code != 422:
                return markets_out
        except Exception as e:
            last_err = e
            print(f"⚠️ Odds API unexpected error: {e}")
            return markets_out

    if odds_data is None:
        if last_err:
            print(f"⚠️ Odds API failed after retries: {last_err}")
        return markets_out

    # Process games ordered by start time for consistency
    for game in sorted(odds_data, key=lambda g: g.get("commence_time") or ""):
        home = game.get("home_team")
        away = game.get("away_team")
        commence_time = game.get("commence_time")

        # Only store games that start today to keep cache focused
        if not _is_today_commence(commence_time):
            continue

        for bookmaker in game.get("bookmakers", []):
            title = bookmaker.get("title") or "FanDuel"

            for market in bookmaker.get("markets", []):
                key = market.get("key")
                if key not in ["h2h", "spreads", "totals"]:
                    continue

                odds_list = market.get("outcomes") or []
                normalized = _normalize_market_entry(
                    sport=sport,
                    home=home,
                    away=away,
                    bookmaker=title,
                    market=key,
                    odds=odds_list,
                    commence_time=commence_time,
                )
                markets_out.append(normalized)

                # Persist for cache reuse
                crud_odds.save_odds(
                    db=db,
                    sport=sport,
                    home_team=home,
                    away_team=away,
                    bookmaker=title,
                    market=key,
                    odds_data=odds_list,
                )

    return markets_out


# ============================================================================
# ⭐ ESPN scoreboard odds (moneyline / spread / totals)
# ============================================================================
def _parse_espn_event(event: Dict, sport: str) -> List[Dict]:
    markets: List[Dict] = []
    for comp in event.get("competitions", []):
        competitors = comp.get("competitors", [])
        home = next(
            (c.get("team", {}).get("displayName") for c in competitors if c.get("homeAway") == "home"),
            None,
        )
        away = next(
            (c.get("team", {}).get("displayName") for c in competitors if c.get("homeAway") == "away"),
            None,
        )
        if not home or not away:
            continue

        commence_time = comp.get("date")
        for odds in comp.get("odds") or []:
            provider = odds.get("provider", {}).get("name") or "ESPN"
            home_odds = odds.get("homeTeamOdds") or {}
            away_odds = odds.get("awayTeamOdds") or {}

            # moneyline
            ml_items = []
            if home_odds.get("moneyLine") is not None:
                ml_items.append({"name": home, "price": home_odds.get("moneyLine")})
            if away_odds.get("moneyLine") is not None:
                ml_items.append({"name": away, "price": away_odds.get("moneyLine")})
            if ml_items:
                markets.append(
                    _normalize_market_entry(
                        sport, home, away, provider, "h2h", ml_items, commence_time
                    )
                )

            # spreads
            spread_value = odds.get("spread")
            if spread_value is not None:
                markets.append(
                    _normalize_market_entry(
                        sport,
                        home,
                        away,
                        provider,
                        "spreads",
                        [
                            {"name": home, "price": home_odds.get("spreadOdds"), "point": spread_value},
                            {"name": away, "price": away_odds.get("spreadOdds"), "point": -spread_value},
                        ],
                        commence_time,
                    )
                )

            # totals
            ou_value = odds.get("overUnder")
            if ou_value is not None:
                over_price = odds.get("overOdds") or home_odds.get("overOdds")
                under_price = odds.get("underOdds") or away_odds.get("underOdds")
                odds_items = []
                if over_price is not None:
                    odds_items.append({"name": "Over", "price": over_price, "point": ou_value})
                if under_price is not None:
                    odds_items.append({"name": "Under", "price": under_price, "point": ou_value})

                if odds_items:
                    markets.append(
                        _normalize_market_entry(
                            sport, home, away, provider, "totals", odds_items, commence_time
                        )
                    )

    return markets


def _espn_date_params(base_date: _dt.date) -> List[Dict]:
    """
    Build a small set of ESPN-friendly date params with fallbacks.
    Includes ISO and compact YYYYMMDD to avoid 400s when ESPN rejects one format.
    """
    candidates: List[Dict] = []
    seen = set()

    def add(param: Dict):
        key = tuple(sorted(param.items()))
        if key in seen:
            return
        seen.add(key)
        candidates.append(param)

    add({"dates": base_date.isoformat()})
    add({"dates": base_date.strftime("%Y%m%d")})
    add({})

    prev = base_date - _dt.timedelta(days=1)
    add({"dates": prev.isoformat()})
    add({"dates": prev.strftime("%Y%m%d")})
    return candidates


async def _fetch_espn_odds(db: Session, sport: str) -> List[Dict]:
    url = ESPN_SCOREBOARD_URLS.get(sport.lower())
    if not url:
        return []

    today = _dt.date.today()
    params_list = _espn_date_params(today)
    headers = {"User-Agent": "Mozilla/5.0 (OddsFetcher/1.0)"}
    markets: List[Dict] = []

    data = None
    soft_statuses = {400, 404, 422}
    last_status = None
    for params in params_list:
        try:
            async with httpx.AsyncClient(timeout=15, headers=headers) as client:
                res = await client.get(url, params=params)
                await asyncio.sleep(2)  # pause between requests to ease rate limits
                res.raise_for_status()
                data = res.json()
                break
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            # 400/404/422 just mean no board for that date/params; move on quietly
            if status not in soft_statuses:
                print(f"⚠️ ESPN odds error ({status}) with params {params}: {e}")
                return markets
            last_status = status
        except Exception as e:
            print(f"⚠️ ESPN odds unexpected error: {e}")
            return markets

    if data is None:
        if last_status:
            print(f"ℹ️ ESPN odds: no scoreboard data after fallbacks (last status={last_status})")
        return markets

    for event in data.get("events", []):
        parsed = _parse_espn_event(event, sport)
        markets.extend(parsed)

        # persist ESPN-derived markets for caching/reuse
        for market in parsed:
            crud_odds.save_odds(
                db=db,
                sport=sport,
                home_team=market.get("home_team"),
                away_team=market.get("away_team"),
                bookmaker=market.get("bookmaker"),
                market=market.get("market"),
                odds_data=market.get("odds"),
            )

    return markets


# ============================================================================
# ⭐ Odds API (full games list + markets + limited props)
# ============================================================================
async def _fetch_odds_api(db: Session, sport: str) -> Tuple[List[Dict], List[Dict]]:
    sport_key = SPORT_MAP.get(sport)
    if not sport_key or not API_KEY:
        return [], []

    team_markets: List[Dict] = []
    prop_markets: List[Dict] = []

    # Fetch core team markets first, then a second call for richer/player markets.
    market_options = [DEFAULT_MARKETS, get_markets_for_sport(sport)]
    for markets in market_options:
        url = (
            f"{BASE_URL}/{sport_key}/odds/"
            f"?apiKey={API_KEY}"
            f"&regions=us"
            f"&markets={markets}"
            f"&bookmakers=fanduel"
            f"&oddsFormat=american"
        )

        print(f"📡 Fetching OddsAPI for {sport} with markets: {markets}")

        odds_data = None
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                res = await client.get(url)
                await asyncio.sleep(2)  # pause between requests to ease rate limits
                res.raise_for_status()
                odds_data = res.json()
        except httpx.HTTPStatusError as e:
            # OddsAPI returns 422 if a market set isn't supported; skip to next.
            if e.response.status_code != 422:
                print(f"⚠️ OddsAPI HTTP error for markets={markets}: {e}")
                continue
        except Exception as e:
            print(f"⚠️ OddsAPI unexpected error for markets={markets}: {e}")
            continue

        if not odds_data:
            continue

        # Ensure deterministic processing order by start time
        for game in sorted(odds_data, key=lambda g: g.get("commence_time") or ""):
            event_id = str(game.get("id") or f"{game.get('home_team')}-{game.get('away_team')}")
            home = game.get("home_team")
            away = game.get("away_team")
            commence_time = game.get("commence_time")
            game_row = crud_odds.upsert_game(
                db=db,
                sport=sport,
                event_id=event_id,
                home_team=home,
                away_team=away,
                commence_time=commence_time,
                source="odds_api",
            )

            for bookmaker in game.get("bookmakers", []):
                title = bookmaker.get("title") or "OddsAPI"
                for market in bookmaker.get("markets", []):
                    key = market.get("key")
                    outcomes = market.get("outcomes") or []

                    if key in ["h2h", "spreads", "totals"]:
                        normalized = _normalize_market_entry(
                            sport=sport,
                            home=home,
                            away=away,
                            bookmaker=title,
                            market=key,
                            odds=outcomes,
                            commence_time=commence_time,
                        )
                        team_markets.append(normalized)
                        crud_odds.upsert_team_market(
                            db=db,
                            game_id=game_row.id,
                            sport=sport,
                            bookmaker=title,
                            market=key,
                            odds_data=outcomes,
                            commence_time=commence_time,
                        )
                    elif key and key.startswith("player_"):
                        stat_type = key.replace("player_", "")
                        prop_entries = []
                        for o in outcomes:
                            player = o.get("name")
                            line = o.get("point")
                            price = o.get("price")
                            side = o.get("description") or o.get("side")

                            if not player:
                                continue
                            crud_odds.upsert_player_prop(
                                db=db,
                                game_id=game_row.id,
                                sport=sport,
                                bookmaker=title,
                                player=player,
                                stat_type=stat_type,
                                side=side,
                                line=line,
                                price=price,
                            )
                            prop_entries.append(
                                _normalize_player_prop_odds_entry(player, stat_type, side, line, price)
                            )

                        if prop_entries:
                            prop_markets.append(
                                _normalize_market_entry(
                                    sport=sport,
                                    home=home,
                                    away=away,
                                    bookmaker=title,
                                    market=key,
                                    odds=prop_entries,
                                    commence_time=commence_time,
                                )
                            )

    return team_markets, prop_markets


# ============================================================================
# ⭐ FanDuel scrape for missing props (best-effort)
# ============================================================================
async def _scrape_fanduel_props(
    db: Session,
    sport: str,
    game_row,
    existing_stat_types: set,
) -> List[Dict]:
    """
    Best-effort FanDuel scrape by event_id. If FanDuel structure changes,
    this will safely no-op.
    """
    event_id = game_row.event_id
    url = f"https://sportsbook.fanduel.com/cache/psmg/odds/v1/3/events/{event_id}.json"
    headers = {"User-Agent": "Mozilla/5.0 (OddsFetcher/1.0)"}
    props: List[Dict] = []

    try:
        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            res = await client.get(url)
            res.raise_for_status()
            text = res.text or ""
            content_type = res.headers.get("content-type", "").lower()
            if not text.strip() or "json" not in content_type:
                return props
            try:
                data = res.json()
            except Exception:
                return props
    except Exception as e:
        print(f"⚠️ FanDuel scrape error for {event_id}: {e}")
        return props

    markets = data.get("attachments", {}).get("markets") or data.get("markets") or []
    for m in markets:
        stat_type = m.get("marketName") or m.get("marketType")
        if not stat_type:
            continue
        stat_type_norm = stat_type.lower().replace(" ", "_")
        if stat_type_norm in existing_stat_types:
            continue

        outcomes = m.get("outcomes") or m.get("runners") or []
        odds_list = []
        for o in outcomes:
            player = o.get("runnerName") or o.get("name")
            price = o.get("price") or o.get("americanOdds") or o.get("oddsAmerican")
            line = o.get("handicap") or o.get("line")
            side = o.get("side") or o.get("description")
            if not player:
                continue
            crud_odds.upsert_player_prop(
                db=db,
                game_id=game_row.id,
                sport=sport,
                bookmaker="FanDuel",
                player=player,
                stat_type=stat_type_norm,
                side=side,
                line=line,
                price=price,
            )
            odds_list.append(_normalize_player_prop_odds_entry(player, stat_type_norm, side, line, price))

        if odds_list:
            props.append(
                _normalize_market_entry(
                    sport=sport,
                    home=game_row.home_team,
                    away=game_row.away_team,
                    bookmaker="FanDuel",
                    market=f"player_{stat_type_norm}",
                    odds=odds_list,
                    commence_time=game_row.commence_time,
                )
            )

    return props


def _normalize_cached_markets(team_rows, prop_rows):
    markets: List[Dict] = []

    for tm, game in team_rows:
        markets.append(
            _normalize_market_entry(
                sport=tm.sport,
                home=game.home_team,
                away=game.away_team,
                bookmaker=tm.bookmaker,
                market=tm.market,
                odds=tm.odds_data or [],
                commence_time=tm.commence_time or game.commence_time,
            )
        )

    for pp, game in prop_rows:
        odds_entry = _normalize_player_prop_odds_entry(
            player=pp.player,
            stat_type=pp.stat_type,
            side=pp.side,
            line=pp.line,
            price=pp.price,
        )
        markets.append(
            _normalize_market_entry(
                sport=pp.sport,
                home=game.home_team,
                away=game.away_team,
                bookmaker=pp.bookmaker,
                market=f"player_{pp.stat_type}",
                odds=[odds_entry],
                commence_time=game.commence_time,
            )
        )

    return markets


async def get_odds_data(db: Session, sport: str, force_refresh: bool = False):
    """
    Fetch odds from cache, OddsAPI (FanDuel) team markets + limited props, scrape FanDuel props,
    and ESPN scoreboard. Returns AI-ready market dictionaries.
    """
    if not force_refresh:
        team_rows = crud_odds.get_recent_team_markets(db, sport, max_age_hours=MAX_CACHE_HOURS)
        prop_rows = crud_odds.get_recent_player_props(db, sport, max_age_hours=MAX_CACHE_HOURS)
        cached = _normalize_cached_markets(team_rows, prop_rows)
        if cached:
            return {"source": "cache", "data": cached}

    all_markets: List[Dict] = []

    # OddsAPI (team + limited props)
    oddsapi_team, oddsapi_props = await _fetch_odds_api(db, sport)
    all_markets.extend(oddsapi_team)
    all_markets.extend(oddsapi_props)

    # FanDuel via OddsAPI for core markets (redundant but faster cache)
    fd_markets = await _fetch_fanduel_odds(db, sport)
    all_markets.extend(fd_markets)

    # ESPN scoreboard odds
    espn_markets = await _fetch_espn_odds(db, sport)
    all_markets.extend(espn_markets)

    # FanDuel scrape for missing props
    try:
        from models.game import Game
        from models.player_prop import PlayerProp

        games = db.query(Game).filter(Game.sport == sport).all()
        for game_row in games:
            existing = db.query(PlayerProp).filter(PlayerProp.game_id == game_row.id).all()
            existing_stats = {p.stat_type for p in existing}
            scraped = await _scrape_fanduel_props(db, sport, game_row, existing_stats)
            all_markets.extend(scraped)
            await asyncio.sleep(0.2)  # avoid hammering FanDuel
    except Exception as e:
        print(f"⚠️ FanDuel scrape loop error: {e}")

    all_markets = _dedupe_markets(all_markets)

    if not all_markets:
        return {
            "source": "error",
            "data": [],
            "error": "no_odds_available",
            "detail": "No odds returned from any source",
        }

    return {
        "source": "api",
        "data": all_markets,
    }
