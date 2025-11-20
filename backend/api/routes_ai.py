from collections import defaultdict
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from utils.config import OPENAI_API_KEY
from utils.sport_detector import detect_sport
from utils.response import success_response
from utils.grok_fetcher import get_trending_sport_tweets
from models.ai_log import AILog
from database.connection import get_db
from models.game_odds import GameOdds
from services.odds_service import get_odds_data
from crud.parlay import save_parlay
from utils.json_utils import extract_json_block
from utils.number_utils import to_float

import json
from typing import Iterable, Optional

# ================================================================
# 🔥 OpenAI v1 Client
# ================================================================
import httpx
from openai import OpenAI

# httpx 0.28 renamed the `proxies` kwarg, so we pass our own client to avoid
# the OpenAI SDK instantiating one with unsupported parameters.
_http_client = httpx.Client()
client = OpenAI(api_key=OPENAI_API_KEY, http_client=_http_client)

router = APIRouter(prefix="/ai", tags=["AI"])


class ChatRequest(BaseModel):
    message: str


def _content_to_text(content: Optional[Iterable]) -> str:
    """
    OpenAI streaming returns structured content parts.
    Convert those pieces into a single text chunk.
    """
    if not content:
        return ""

    if isinstance(content, str):
        return content

    text_parts = []
    for part in content:
        if isinstance(part, str):
            text_parts.append(part)
        elif isinstance(part, dict):
            text = part.get("text")
            if text:
                text_parts.append(text)
        else:
            text = getattr(part, "text", None)
            if text:
                text_parts.append(text)
    return "".join(text_parts)


def _chunk_text(chunk) -> str:
    """Extract text from a ChatCompletionChunk object."""
    if not chunk or not getattr(chunk, "choices", None):
        return ""

    choice = chunk.choices[0]
    delta = getattr(choice, "delta", None)
    if not delta:
        return ""
    content = getattr(delta, "content", None)
    return _content_to_text(content)


# ================================================================
# 📌 NON-STREAM PARLAY ENDPOINT — OPENAI v1
# ================================================================
@router.post("/parlay")
async def parlay(request: ChatRequest, db: Session = Depends(get_db)):
    sport = detect_sport(request.message)
    tweets = get_trending_sport_tweets(sport)
    context = "\n".join(tweets)

    # 🧠 1️⃣ Get odds (cached or live)
    odds_result = await get_odds_data(db, sport)
    raw_odds = odds_result["data"]

    # Group odds by game and normalize structure
    game_map = defaultdict(list)
    for row in raw_odds:
        if isinstance(row, GameOdds):
            key = f"{row.home_team} vs {row.away_team}"
            game_map[key].append({
                "home_team": row.home_team,
                "away_team": row.away_team,
                "bookmaker": row.bookmaker,
                "market": row.market,
                "odds": row.odds_data,
            })
            continue

        home_team = row.get("home_team")
        away_team = row.get("away_team")
        if not home_team or not away_team:
            continue

        key = f"{home_team} vs {away_team}"
        bookmakers = row.get("bookmakers") or []
        if not bookmakers:
            game_map[key].append({
                "home_team": home_team,
                "away_team": away_team,
                "bookmaker": "Unknown",
                "market": "unknown",
                "odds": row.get("odds") or [],
            })
            continue

        for bookmaker in bookmakers:
            title = bookmaker.get("title") or "Unknown"
            for market in bookmaker.get("markets", []):
                game_map[key].append({
                    "home_team": home_team,
                    "away_team": away_team,
                    "bookmaker": title,
                    "market": market.get("key"),
                    "odds": market.get("outcomes"),
                })

    # Convert to list of 30 games max
    odds_data = []
    for game, entries in list(game_map.items())[:30]:
        if not entries:
            continue
        entry = entries[0]
        odds_data.append({
            "home_team": entry["home_team"],
            "away_team": entry["away_team"],
            "bookmaker": entry.get("bookmaker") or "Unknown",
            "market": entry.get("market") or "unknown",
            "odds": entry.get("odds"),
        })

    # Format readable odds
    odds_text = ""
    for o in odds_data:
        odds_text += f"{o['home_team']} vs {o['away_team']} ({o['bookmaker']} - {o['market']}): {o['odds']}\n"

    # Build prompt
    prompt = (
        f"User request: {request.message}\n"
        f"Sport detected: {sport}\n\n"
        f"Odds Data:\n{odds_text}\n\n"
        f"Generate a 3–5 leg parlay using these odds. "
        f"Return ONLY JSON. Keys: parlay, total_odds, potential_payout, reasoning."
    )

    print("\n🔥 Sending prompt (trimmed):", prompt[:500])

    # 📌 OPENAI v1 CALL
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert AI sports betting assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=900,
        temperature=0.8,
    )

    reply = completion.choices[0].message.content.strip()
    print("💰 GPT Reply (trimmed):", reply[:500])

    # Log event
    log = AILog(
        user_message=request.message,
        detected_sport=sport,
        grok_context=context,
        ai_prompt=prompt,
        ai_response=reply,
    )
    db.add(log)
    db.commit()

    # Extract JSON
    parsed = extract_json_block(reply)

    # Save parlay
    saved_parlay = None
    if parsed:
        try:
            saved_parlay = save_parlay(
                db,
                sport,
                parsed.get("parlay", []),
                to_float(parsed.get("total_odds")),
                to_float(parsed.get("potential_payout")),
                reply
            )
            print("✅ Parlay saved.")
        except Exception as e:
            print("⚠️ Save error:", e)

    return success_response("AI parlay generated", {
        "raw_text": reply,
        "parsed_parlay": parsed,
        "saved": bool(saved_parlay),
    })

@router.post("/chat-stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    user_message = request.message
    sport = detect_sport(user_message)

    print("\n🔥 Streaming Request:", user_message)

    # Match the non-streaming endpoint: pull odds and build structured prompt
    odds_result = await get_odds_data(db, sport)
    raw_odds = odds_result["data"]

    game_map = defaultdict(list)
    for row in raw_odds:
        if isinstance(row, GameOdds):
            key = f"{row.home_team} vs {row.away_team}"
            game_map[key].append({
                "home_team": row.home_team,
                "away_team": row.away_team,
                "bookmaker": row.bookmaker,
                "market": row.market,
                "odds": row.odds_data,
            })
            continue

        home_team = row.get("home_team")
        away_team = row.get("away_team")
        if not home_team or not away_team:
            continue

        key = f"{home_team} vs {away_team}"
        bookmakers = row.get("bookmakers") or []
        if not bookmakers:
            game_map[key].append({
                "home_team": home_team,
                "away_team": away_team,
                "bookmaker": "Unknown",
                "market": "unknown",
                "odds": row.get("odds") or [],
            })
            continue

        for bookmaker in bookmakers:
            title = bookmaker.get("title") or "Unknown"
            for market in bookmaker.get("markets", []):
                game_map[key].append({
                    "home_team": home_team,
                    "away_team": away_team,
                    "bookmaker": title,
                    "market": market.get("key"),
                    "odds": market.get("outcomes"),
                })

    odds_data = []
    for game, entries in list(game_map.items())[:30]:
        if not entries:
            continue
        entry = entries[0]
        odds_data.append({
            "home_team": entry["home_team"],
            "away_team": entry["away_team"],
            "bookmaker": entry.get("bookmaker") or "Unknown",
            "market": entry.get("market") or "unknown",
            "odds": entry.get("odds"),
        })

    odds_text = ""
    for o in odds_data:
        odds_text += f"{o['home_team']} vs {o['away_team']} ({o['bookmaker']} - {o['market']}): {o['odds']}\n"

    base_prompt = (
        f"User request: {user_message}\n"
        f"Sport detected: {sport}\n\n"
        f"Odds Data:\n{odds_text}\n\n"
    )

    prompt = (
        base_prompt +
        "Stream a short helpful response. At the very end, emit ONE JSON object "
        "with keys: parlay, total_odds, potential_payout, reasoning. "
        "Parlay should be an array of legs with team/selection, market, odds, and reason."
    )

    json_only_prompt = (
        base_prompt +
        "Return ONLY JSON, no prose. Keys: parlay (array of legs with team/selection, market, odds, reason), "
        "total_odds, potential_payout, reasoning."
    )

    def generate():
        print("🚀 Starting streaming...")

        full_text = ""  # collect entire response here

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert AI sports betting assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=900,
            temperature=0.8,
            stream=True,
        )

        # 1️⃣ Stream and collect
        for event in stream:
            chunk = _chunk_text(event)
            if chunk:
                full_text += chunk
                yield chunk  # send to client immediately

        print("🏁 Stream finished. Extracting parlay JSON...")

        # 2️⃣ Extract JSON
        parsed = extract_json_block(full_text)

        saved_parlay = None

        # Fallback: if model ignored JSON instruction during stream, re-run a short JSON-only call
        if not parsed:
            try:
                retry = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are an expert AI sports betting assistant."},
                        {"role": "user", "content": json_only_prompt},
                    ],
                    max_tokens=900,
                    temperature=0.4,
                )
                retry_reply = retry.choices[0].message.content.strip()
                parsed = extract_json_block(retry_reply)
                if parsed:
                    print("✅ Fallback JSON generated after stream.")
            except Exception as e:
                print("⚠️ Fallback JSON error:", e)

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
                print("✅ Parlay saved (stream mode).")
            except Exception as e:
                print("⚠️ Save error:", e)

        # 3️⃣ After streaming ends, send final structured JSON
        final = {
            "parsed_parlay": parsed,
            "saved": bool(saved_parlay),
        }

        yield f"\n\n[[FINAL_JSON]]{json.dumps(final)}[[/FINAL_JSON]]"

    return StreamingResponse(generate(), media_type="text/plain")
