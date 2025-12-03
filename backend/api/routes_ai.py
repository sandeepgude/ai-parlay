import datetime as dt
from zoneinfo import ZoneInfo
from collections import defaultdict
from typing import Iterable, Optional, List, Dict, Any

import json
import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from utils.config import OPENAI_API_KEY
from utils.sport_detector import detect_sport
from utils.response import success_response
from database.connection import get_db
from models.ai_log import AILog
from crud.parlay import save_parlay
from services.odds_service import get_odds_data
from services.team_stats import get_team_stats, get_player_stats
from utils.json_utils import extract_json_block
from utils.number_utils import to_float
from utils.prompt_builder import build_parlay_prompt

from openai import OpenAI

# ================================================================
# 🔥 OpenAI v1 Client with shared httpx client
# ================================================================
_http_client = httpx.Client()
client = OpenAI(api_key=OPENAI_API_KEY, http_client=_http_client)

router = APIRouter(prefix="/ai", tags=["AI"])


class ChatRequest(BaseModel):
    message: str


# ================================================================
# 🔧 Helpers: streaming → text
# ================================================================
def _content_to_text(content: Optional[Iterable]) -> str:
    """
    OpenAI streaming returns structured content parts.
    Convert those pieces into a single text chunk.
    """
    if not content:
        return ""

    if isinstance(content, str):
        return content

    parts: List[str] = []
    for part in content:
        if isinstance(part, str):
            parts.append(part)
        elif isinstance(part, dict):
            text = part.get("text")
            if text:
                parts.append(text)
        else:
            text = getattr(part, "text", None)
            if text:
                parts.append(text)
    return "".join(parts)


def _chunk_text(chunk) -> str:
    """
    Extract plain text from a ChatCompletionChunk object.
    Works with OpenAI v1 streaming responses.
    """
    if not chunk or not getattr(chunk, "choices", None):
        return ""

    choice = chunk.choices[0]
    delta = getattr(choice, "delta", None)
    if not delta:
        return ""
    content = getattr(delta, "content", None)
    return _content_to_text(content)


def _parse_parlay_json(text: str):
    """
    Try several strategies to extract a JSON object describing the parlay.
    """
    if not text:
        return None

    parsed = extract_json_block(text)
    if parsed:
        return parsed

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            pass

    return None


# ================================================================
# 🔧 Helper: Normalize odds for AI (handles ORM + dict)
# ================================================================
def _normalize_single_game(game: Any) -> Optional[Dict[str, Any]]:
    """
    Convert any GameOdds-style object or dict into a clean AI-friendly dict:

    {
      "home_team": str,
      "away_team": str,
      "sport": "nba" | "nfl" | ...,
      "bookmaker": str,
      "market": str,
      "odds": [
        {"name": "Orlando Magic", "price": 1.45},
        ...
      ],
      "commence_time": str | None
    }
    """
    # If it's already a dict, just map the fields
    if isinstance(game, dict):
        home = game.get("home_team")
        away = game.get("away_team")
        odds = game.get("odds") or []
        bookmaker = game.get("bookmaker")
        # 🏦 Filter to FanDuel only to keep prompts consistent and smaller
        if bookmaker and str(bookmaker).lower() != "fanduel":
            return None
        if not home or not away or not odds:
            return None

        return {
            "home_team": home,
            "away_team": away,
            "sport": game.get("sport"),
            "bookmaker": bookmaker,
            "market": game.get("market"),
            "odds": odds,
            "commence_time": game.get("commence_time"),
        }

    # Otherwise assume it's an ORM object (GameOdds)
    def attr(name: str, default=None):
        return getattr(game, name, default)

    home = attr("home_team")
    away = attr("away_team")
    if not home or not away:
        return None

    # Odds may be stored as Python list/dict or JSON string
    raw_odds = attr("odds") or attr("odds_json") or attr("odds_data")
    if isinstance(raw_odds, str):
        try:
            odds = json.loads(raw_odds)
        except Exception:
            odds = []
    else:
        odds = raw_odds or []

    bookmaker = attr("bookmaker")
    # 🏦 Filter to FanDuel only to keep prompts consistent and smaller
    if bookmaker and str(bookmaker).lower() != "fanduel":
        return None

    if not odds:
        return None

    return {
        "home_team": home,
        "away_team": away,
        "sport": attr("sport"),
        "bookmaker": bookmaker,
        "market": attr("market"),
        "odds": odds,
        "commence_time": attr("commence_time"),
    }


def normalize_odds_for_ai(raw_items: Iterable[Any]) -> List[Dict[str, Any]]:
    """
    Take whatever get_odds_data() returned (ORM rows or dicts) and produce
    a clean, serializable list for prompts AND stats builder.
    """
    normalized: List[Dict[str, Any]] = []

    for g in raw_items:
        try:
            ng = _normalize_single_game(g)
            if ng:
                normalized.append(ng)
        except Exception as e:
            print(f"⚠️ Failed to normalize odds row {g!r}: {e}")

    print(f"🧾 Odds rows (normalized): {len(normalized)}")
    if normalized:
        print("   sample row:", normalized[0])

    return normalized


MOUNTAIN_TZ = ZoneInfo("America/Denver")


def _is_today_commence(commence_time: Any) -> bool:
    """Return True if commence_time is today in Mountain Time."""
    if not commence_time:
        return False
    try:
        if isinstance(commence_time, str):
            ts = commence_time.replace("Z", "+00:00")
            dt_obj = dt.datetime.fromisoformat(ts)
        elif isinstance(commence_time, dt.datetime):
            dt_obj = commence_time
        elif isinstance(commence_time, dt.date):
            return commence_time == dt.datetime.now(MOUNTAIN_TZ).date()
        else:
            return False

        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=dt.timezone.utc)
        local_dt = dt_obj.astimezone(MOUNTAIN_TZ)
        return local_dt.date() == dt.datetime.now(MOUNTAIN_TZ).date()
    except Exception:
        return False


def filter_today_odds(odds_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter odds to only games commencing today (UTC)."""
    return [g for g in odds_data if _is_today_commence(g.get("commence_time"))]


# ================================================================
# 🔧 Helper: Build Team + Player stats for relevant games (Mode A)
# ================================================================
async def build_stats_for_games(
    odds_data: List[Dict[str, Any]],
    sport: str,
    db: Session,
) -> Dict[str, Dict[str, Any]]:
    """
    For every game in odds_data:
      - Fetch team stats for home & away
      - Fetch player stats for any players appearing in player props (optional)

    odds_data is expected to contain dicts like:
      {
        "home_team": "...",
        "away_team": "...",
        "sport": "...",
        "bookmaker": "...",
        "market": "...",
        "odds": [...],
        "player_props": [{ "player": "...", ... }, ...]  # optional
      }
    """
    team_stats: Dict[str, Any] = {}
    player_stats: Dict[str, Any] = {}

    def _field(game_obj: Dict[str, Any], key: str):
        # odds_data should now be dicts, but keep this defensive
        if isinstance(game_obj, dict):
            return game_obj.get(key)
        return getattr(game_obj, key, None)

    for game in odds_data:
        home = _field(game, "home_team")
        away = _field(game, "away_team")

        # 1️⃣ Team stats
        if home and home not in team_stats:
            try:
                ts = await get_team_stats(sport, home, db=db)
                if ts:
                    team_stats[home] = ts
            except Exception as e:
                print(f"⚠️ Team stats error for {home}: {e}")

        if away and away not in team_stats:
            try:
                ts = await get_team_stats(sport, away, db=db)
                if ts:
                    team_stats[away] = ts
            except Exception as e:
                print(f"⚠️ Team stats error for {away}: {e}")

        # 2️⃣ Player stats (if you wire player_props in odds_service)
        props = _field(game, "player_props") or []
        for prop in props:
            pname = prop.get("player")
            if not pname or pname in player_stats:
                continue
            try:
                ps = await get_player_stats(sport, pname, db=db)
                if ps:
                    player_stats[pname] = ps
            except Exception as e:
                print(f"⚠️ Player stats error for {pname}: {e}")

    return {"teams": team_stats, "players": player_stats}


# ================================================================
# 📌 NON-STREAM PARLAY ENDPOINT — OPENAI v1
# ================================================================
@router.post("/parlay")
async def parlay(request: ChatRequest, db: Session = Depends(get_db)):
    sport = detect_sport(request.message)
    print(f"\n🔥 Non-stream parlay request: {request.message} (sport: {sport})")

    # 1️⃣ Get odds (cached or live)
    try:
        odds_result = await get_odds_data(db, sport)
        if odds_result.get("source") == "error":
            print("⚠️ Odds service error (non-stream):", odds_result.get("detail"))
            raw_odds: List[Any] = []
        else:
            raw_odds = list(odds_result.get("data") or [])
    except Exception as e:
        print("⚠️ Odds fetch error (non-stream):", e)
        raw_odds = []

    # 2️⃣ Normalize odds for AI
    odds_data = normalize_odds_for_ai(raw_odds)
    odds_data = filter_today_odds(odds_data)
    print(f"📅 Filtered to today's games: {len(odds_data)}")
    # keep prompt compact
    odds_data = odds_data[:15]  # limit games for prompt size

    # 3️⃣ Build team + player stats block
    stats_block = await build_stats_for_games(odds_data, sport, db)

    # 4️⃣ Build master parlay prompt
    prompt = build_parlay_prompt(
        user_message=request.message,
        sport=sport,
        odds=odds_data,
        team_stats=stats_block["teams"],
        player_stats=stats_block["players"],
    )

    print("\n🔥 Prompt (non-stream, trimmed):")
    print(prompt[:800])
    print("🧠 Prompt length (chars):", len(prompt))
    print("📝 Full prompt (non-stream, capped 2000 chars):")
    print(prompt[:2000])

    # 5️⃣ Call OpenAI
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an elite sports betting assistant that builds parlays based on odds and stats.",
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=1200,
        temperature=0.8,
        response_format={"type": "json_object"},
    )

    reply = completion.choices[0].message.content.strip()
    print("💬 GPT Reply (non-stream, trimmed):", reply[:800])

    # 6️⃣ Log event
    log = AILog(
        user_message=request.message,
        detected_sport=sport,
        grok_context="",
        ai_prompt=prompt,
        ai_response=reply,
    )
    db.add(log)
    db.commit()

    # 7️⃣ Extract JSON from reply
    parsed = _parse_parlay_json(reply)
    if parsed:
        print("🧾 Parsed parlay (non-stream):", parsed)
    else:
        print("⚠️ Parsed parlay missing (non-stream)")

    # 8️⃣ Save parlay to DB
    saved_parlay = None
    if parsed:
        try:
            saved_parlay = save_parlay(
                db,
                sport,
                parsed.get("parlay", []),
                to_float(parsed.get("total_odds")),
                to_float(parsed.get("potential_payout")),
                reply,
            )
            print("✅ Parlay saved (non-stream).")
        except Exception as e:
            print("⚠️ Save error (non-stream):", e)
    else:
        print("⚠️ Skipped saving — no parsed parlay (non-stream).")

    return success_response(
        "AI parlay generated",
        {
            "raw_text": reply,
            "parsed_parlay": parsed,
            "saved": bool(saved_parlay),
        },
    )


# ================================================================
# 📌 STREAMING PARLAY ENDPOINT — OPENAI v1
# ================================================================
@router.post("/chat-stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    user_message = request.message
    sport = detect_sport(user_message)

    print("\n🔥 Streaming Request:", user_message)
    print("   Detected sport:", sport)

    # 1️⃣ Get odds (cached or live)
    try:
        odds_result = await get_odds_data(db, sport)
        if odds_result.get("source") == "error":
            print("⚠️ Odds service error (stream):", odds_result.get("detail"))
            raw_odds: List[Any] = []
        else:
            raw_odds = list(odds_result.get("data") or [])
    except Exception as e:
        print("⚠️ Odds fetch error (stream):", e)
        raw_odds = []

    # 2️⃣ Normalize odds
    odds_data = normalize_odds_for_ai(raw_odds)
    odds_data = filter_today_odds(odds_data)
    print(f"📅 Filtered to today's games (stream): {len(odds_data)}")
    # keep prompt compact to increase chance of clean JSON
    odds_data = odds_data[:45]

    # 3️⃣ Team + player stats
    stats_block = await build_stats_for_games(odds_data, sport, db)

    # 4️⃣ Build prompt (same as non-stream)
    prompt = build_parlay_prompt(
        user_message=user_message,
        sport=sport,
        odds=odds_data,
        team_stats=stats_block["teams"],
        player_stats=stats_block["players"],
    )
    print("\n🔥 Prompt (stream, trimmed):")
    print(prompt[:800])
    print("🧠 Prompt length (chars):", len(prompt))
    print("📝 Full prompt (stream, capped 2000 chars):")
    print(prompt[:2000])

    # Also build JSON-only variant for fallback
    json_only_prompt = prompt + "\n\nReturn ONLY JSON, no prose."

    def generate():
        print("🚀 Starting streaming...")
        full_text = ""

        # 5️⃣ Stream from OpenAI
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an elite sports betting assistant that builds parlays based on odds and stats.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=1200,
            temperature=0.8,
            stream=True,
        )

        for event in stream:
            chunk = _chunk_text(event)
            if chunk:
                full_text += chunk
                yield chunk  # send to frontend

        print("🏁 Stream finished. Extracting parlay JSON...")

        # 6️⃣ Try to extract JSON from the streamed text
        parsed = _parse_parlay_json(full_text)
        saved_parlay = None

        if parsed:
            print("🧾 Parsed parlay (stream):", parsed)
        else:
            print("⚠️ Parsed parlay missing from stream; trying fallback JSON-only call")

            # 7️⃣ Fallback: one more non-stream JSON-only call
            try:
                retry = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an elite sports betting assistant. Return ONLY JSON.",
                        },
                        {"role": "user", "content": json_only_prompt},
                    ],
                    max_tokens=900,
                    temperature=0.4,
                    response_format={"type": "json_object"},
                )
                retry_reply = retry.choices[0].message.content.strip()
                parsed = _parse_parlay_json(retry_reply)
                if parsed:
                    print("✅ Fallback JSON parsed (stream):", parsed)
            except Exception as e:
                print("⚠️ Fallback JSON error (stream):", e)

        # 8️⃣ Save parlay from stream
        if parsed:
            try:
                saved_parlay = save_parlay(
                    db,
                    sport,
                    parsed.get("parlay", []),
                    to_float(parsed.get("total_odds")),
                    to_float(parsed.get("potential_payout")),
                    full_text,
                )
                print("✅ Parlay saved (stream).")
            except Exception as e:
                print("⚠️ Save error (stream):", e)
        else:
            print("⚠️ Skipped saving — no parsed parlay (stream).")

        # (Optional) Log stream interaction
        try:
            log = AILog(
                user_message=user_message,
                detected_sport=sport,
                grok_context="",
                ai_prompt=prompt,
                ai_response=full_text,
            )
            db.add(log)
            db.commit()
        except Exception as e:
            print("⚠️ Log save error (stream):", e)

        # 9️⃣ Send final JSON marker for frontend to parse
        final_payload = {
            "parsed_parlay": parsed,
            "saved": bool(saved_parlay),
        }
        yield f"\n\n[[FINAL_JSON]]{json.dumps(final_payload)}[[/FINAL_JSON]]"

    return StreamingResponse(generate(), media_type="text/plain")
