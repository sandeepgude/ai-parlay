import httpx
from sqlalchemy.orm import Session

import crud.team_stats as crud_team_stats
import crud.player_stats as crud_player_stats
from utils.config import BALLDONTLIE_KEY

# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------
BALLDONTLIE = "https://api.balldontlie.io/v1"  # ✅ NEW BASE URL

BALLDONTLIE_HEADERS = (
    {"Authorization": f"Bearer {BALLDONTLIE_KEY}"}
    if BALLDONTLIE_KEY
    else {}
)

ESPN_NFL_SCOREBOARD = "https://site.api.espn.com/apis/v2/sports/football/nfl/scoreboard"
ESPN_NFL_SEARCH = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/players?limit=3000"
ESPN_NFL_PLAYER = "https://site.api.espn.com/apis/v2/sports/football/nfl/athletes/{pid}/stats"


# =========================================================
# 🔥 UNIVERSAL NBA TEAM ID LOOKUP (cached, static fallback)
# =========================================================
_nba_team_id_cache: dict[str, int | None] = {}
_nba_team_list_cache: list[dict] | None = None

NBA_TEAM_IDS_STATIC = {
    "atlanta hawks": 1,
    "boston celtics": 2,
    "brooklyn nets": 3,
    "charlotte hornets": 4,
    "chicago bulls": 5,
    "cleveland cavaliers": 6,
    "dallas mavericks": 7,
    "denver nuggets": 8,
    "detroit pistons": 9,
    "golden state warriors": 10,
    "houston rockets": 11,
    "indiana pacers": 12,
    "la clippers": 13,
    "los angeles clippers": 13,
    "los angeles lakers": 14,
    "memphis grizzlies": 15,
    "miami heat": 16,
    "milwaukee bucks": 17,
    "minnesota timberwolves": 18,
    "new orleans pelicans": 19,
    "new york knicks": 20,
    "oklahoma city thunder": 21,
    "orlando magic": 22,
    "philadelphia 76ers": 23,
    "phoenix suns": 24,
    "portland trail blazers": 25,
    "sacramento kings": 26,
    "san antonio spurs": 27,
    "toronto raptors": 28,
    "utah jazz": 29,
    "washington wizards": 30,
}


async def get_nba_team_id(team_name: str):
    """
    Fetch all NBA teams from BallDontLie and find the correct team ID.
    Uses in-memory cache and a static fallback to avoid 429/404 noise.
    """
    team_lower = team_name.lower()

    if team_lower in _nba_team_id_cache:
        return _nba_team_id_cache[team_lower]

    if team_lower in NBA_TEAM_IDS_STATIC:
        _nba_team_id_cache[team_lower] = NBA_TEAM_IDS_STATIC[team_lower]
        return NBA_TEAM_IDS_STATIC[team_lower]

    global _nba_team_list_cache
    if _nba_team_list_cache is None:
        try:
            url = f"{BALLDONTLIE}/teams"
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get(url, headers=BALLDONTLIE_HEADERS)
                res.raise_for_status()
            _nba_team_list_cache = res.json().get("data", [])
        except Exception as e:
            print(f"⚠️ NBA team list fetch failed: {e}")
            _nba_team_list_cache = []

    for t in _nba_team_list_cache:
        if t.get("full_name", "").lower() == team_lower:
            _nba_team_id_cache[team_lower] = t["id"]
            return t["id"]

    print(f"❌ NBA team not found in BallDontLie: {team_name}")
    _nba_team_id_cache[team_lower] = None
    return None


# =========================================================
# 🔥 NBA: Last 5 games
# =========================================================
async def get_last5_games_nba(team_id: int):
    # BallDontLie expects team_ids[]=<id>
    url = f"{BALLDONTLIE}/games?team_ids[]={team_id}&per_page=5"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, headers=BALLDONTLIE_HEADERS)
            res.raise_for_status()
        return res.json().get("data", [])
    except Exception as e:
        print(f"⚠️ get_last5_games_nba error for team_id {team_id}: {e}")
        return []


async def get_nba_team_stats(team_name: str):
    """
    Returns last 5 NBA games with averages.
    Auto-fetches correct team_id using lookup.
    """
    team_id = await get_nba_team_id(team_name)
    if not team_id:
        return None

    games = await get_last5_games_nba(team_id)
    if not games:
        return None

    pts_for, pts_against, totals = [], [], []

    for g in games:
        if g["home_team"]["id"] == team_id:
            pf, pa = g["home_team_score"], g["visitor_team_score"]
        else:
            pf, pa = g["visitor_team_score"], g["home_team_score"]

        pts_for.append(pf)
        pts_against.append(pa)
        totals.append(pf + pa)

    return {
        "team": team_name,
        "sport": "nba",
        "games_count": len(games),
        "last5_points_for": pts_for,
        "last5_points_against": pts_against,
        "avg_points_for": sum(pts_for) / len(pts_for),
        "avg_points_against": sum(pts_against) / len(pts_against),
        "avg_total": sum(totals) / len(totals),
    }


# =========================================================
# 🔥 NFL TEAM STATS (Last 5 Games)
# =========================================================
async def get_last5_games_nfl(team_name: str):
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(ESPN_NFL_SCOREBOARD)
        res.raise_for_status()

    events = res.json().get("events", [])
    team_lower = team_name.lower()

    found_games = []

    for game in events:
        competitors = game["competitions"][0]["competitors"]
        names = [c["team"]["displayName"].lower() for c in competitors]

        if team_lower in names:
            found_games.append(game)

        if len(found_games) >= 5:
            break

    return found_games


async def get_nfl_team_stats(team_name: str):
    games = await get_last5_games_nfl(team_name)
    if not games:
        return None

    pts_for, pts_against, totals = [], [], []

    for g in games:
        comp = g["competitions"][0]
        home = comp["competitors"][0]
        away = comp["competitors"][1]

        if team_name.lower() in home["team"]["displayName"].lower():
            pf, pa = int(home["score"]), int(away["score"])
        else:
            pf, pa = int(away["score"]), int(home["score"])

        pts_for.append(pf)
        pts_against.append(pa)
        totals.append(pf + pa)

    return {
        "team": team_name,
        "sport": "nfl",
        "games_count": len(games),
        "last5_points_for": pts_for,
        "last5_points_against": pts_against,
        "avg_points_for": sum(pts_for) / len(pts_for),
        "avg_points_against": sum(pts_against) / len(pts_against),
        "avg_total": sum(totals) / len(totals),
    }


# =========================================================
# 🔥 TEAM STATS WITH DB CACHE
# =========================================================
async def _fetch_live_team_stats(sport: str, team: str):
    sport = sport.lower()
    if sport == "nba":
        return await get_nba_team_stats(team)
    if sport == "nfl":
        return await get_nfl_team_stats(team)
    return None


async def get_team_stats(sport: str, team_name: str, db: Session | None = None, max_age_hours=3):
    """
    Returns team stats from cache or fetches live.
    """
    sport = sport.lower()

    if db:
        cached = crud_team_stats.get_recent_team_stats(db, sport, team_name, max_age_hours)
        if cached:
            return cached.stats

        crud_team_stats.delete_team_stats(db, sport, team_name)

    live = await _fetch_live_team_stats(sport, team_name)

    if live and db:
        crud_team_stats.save_team_stats(db, sport, team_name, live)

    return live


# =========================================================
# 🔥 NBA PLAYER STATS
# =========================================================
async def search_nba_player_id(name: str):
    url = f"{BALLDONTLIE}/players?search={name}"
    async with httpx.AsyncClient(timeout=8) as client:
        res = await client.get(url, headers=BALLDONTLIE_HEADERS)
        res.raise_for_status()

    data = res.json().get("data", [])
    return data[0]["id"] if data else None


async def get_nba_player_stats(name: str):
    pid = await search_nba_player_id(name)
    if not pid:
        return None

    url = f"{BALLDONTLIE}/stats?player_ids={pid}&per_page=5"

    async with httpx.AsyncClient(timeout=8) as client:
        res = await client.get(url, headers=BALLDONTLIE_HEADERS)
        res.raise_for_status()

    rows = res.json().get("data", [])
    if not rows:
        return None

    pts, reb, ast, threes = [], [], [], []

    for g in rows:
        pts.append(g["pts"])
        reb.append(g["reb"])
        ast.append(g["ast"])
        threes.append(g["fg3m"])

    return {
        "player": name,
        "sport": "nba",
        "games_count": len(rows),
        "last5_points": pts,
        "last5_rebounds": reb,
        "last5_assists": ast,
        "last5_threes": threes,
        "avg_points": sum(pts) / len(pts),
        "avg_rebounds": sum(reb) / len(reb),
        "avg_assists": sum(ast) / len(ast),
        "avg_threes": sum(threes) / len(threes),
    }


# =========================================================
# 🔥 NFL PLAYER STATS (ESPN)
# =========================================================
async def search_nfl_player_id(name: str):
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(ESPN_NFL_SEARCH)
        res.raise_for_status()

    items = res.json().get("items", [])

    nm = name.lower()
    for p in items:
        if nm in p["displayName"].lower():
            return p["id"]

    return None


async def get_nfl_player_stats(name: str):
    pid = await search_nfl_player_id(name)
    if not pid:
        return None

    url = ESPN_NFL_PLAYER.format(pid=pid)

    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(url)
        res.raise_for_status()

    data = res.json()
    categories = data.get("splits", {}).get("categories", [])

    stats = {
        "player": name,
        "sport": "nfl",
        "passing_yards": [],
        "rushing_yards": [],
        "receiving_yards": [],
        "targets": [],
        "touchdowns": [],
    }

    for cat in categories:
        label = cat.get("name", "").lower()

        for s in cat.get("stats", []):
            comps = s.get("athlete", {}).get("competitions", [])
            if not comps:
                continue

            comp = comps[0]

            if label == "passing":
                stats["passing_yards"].append(int(comp.get("passingYards", 0)))

            if label == "rushing":
                stats["rushing_yards"].append(int(comp.get("rushingYards", 0)))

            if label == "receiving":
                stats["receiving_yards"].append(int(comp.get("receivingYards", 0)))
                stats["targets"].append(int(comp.get("targets", 0)))

            if "touchdowns" in label:
                stats["touchdowns"].append(int(comp.get("touchdowns", 0)))

    # Only last 5 games
    for key in stats:
        if isinstance(stats[key], list):
            stats[key] = stats[key][:5]

    return stats


# =========================================================
# 🔥 PLAYER STATS CACHED
# =========================================================
async def _fetch_live_player_stats(sport, name):
    sport = sport.lower()
    if sport == "nba":
        return await get_nba_player_stats(name)
    if sport == "nfl":
        return await get_nfl_player_stats(name)
    return None


async def get_player_stats(sport: str, name: str, db: Session | None = None, max_age_hours=3):
    sport = sport.lower()

    if db:
        cached = crud_player_stats.get_recent_player_stats(db, sport, name, max_age_hours)
        if cached:
            return cached.stats

        crud_player_stats.delete_player_stats(db, sport, name)

    live = await _fetch_live_player_stats(sport, name)

    if live and db:
        crud_player_stats.save_player_stats(db, sport, name, live)

    return live
