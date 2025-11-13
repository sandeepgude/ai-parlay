from collections import defaultdict
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from openai import OpenAI
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

router = APIRouter(prefix="/ai", tags=["AI"])
client = OpenAI(api_key=OPENAI_API_KEY)

class ChatRequest(BaseModel):
    message: str


@router.post("/parlay")
async def parlay(request: ChatRequest, db: Session = Depends(get_db)):
    sport = detect_sport(request.message)
    tweets = get_trending_sport_tweets(sport)
    context = "\n".join(tweets)

    # 🧠 1️⃣ Get odds (cached or live)
    odds_result = await get_odds_data(db, sport)
    raw_odds = odds_result["data"]

    # 🧩 2️⃣ Group odds by unique games (home vs away)
    game_map = defaultdict(list)
    for row in raw_odds:
        if isinstance(row, GameOdds):
            key = f"{row.home_team} vs {row.away_team}"
            game_map[key].append(row)
        elif isinstance(row, dict):
            key = f"{row.get('home_team')} vs {row.get('away_team')}"
            game_map[key].append(row)

    # 🧩 3️⃣ Pick up to 30 unique matchups
    odds_data = []
    for game, entries in list(game_map.items())[:30]:
        entry = entries[0]
        if isinstance(entry, GameOdds):
            odds_data.append({
                "home_team": entry.home_team,
                "away_team": entry.away_team,
                "bookmaker": entry.bookmaker,
                "market": entry.market,
                "odds": entry.odds_data,
            })
        else:
            odds_data.append({
                "home_team": entry.get("home_team"),
                "away_team": entry.get("away_team"),
                "bookmaker": entry.get("bookmaker"),
                "market": entry.get("market"),
                "odds": entry.get("odds"),
            })

    # 🧩 4️⃣ Format for prompt
    odds_text = ""
    for o in odds_data:
        home, away = o.get("home_team", ""), o.get("away_team", "")
        bookmaker, market = o.get("bookmaker", ""), o.get("market", "")
        odds = o.get("odds", "")
        odds_text += f"{home} vs {away} ({bookmaker} - {market}): {odds}\n"

    # 🧠 5️⃣ Build the AI prompt
    prompt = (
        f"User request: {request.message}\n"
        f"Sport detected: {sport}\n\n"
        f"Current odds data (latest {len(odds_data)} games):\n{odds_text}\n\n"
        f"Generate a 3–5 leg parlay using these odds. "
        f"For each leg, include reasoning, bookmaker, and implied value. "
        f"Return valid JSON only (no markdown), with keys: parlay[], total_odds, potential_payout, reasoning. "
        f"Ensure all numeric fields are numbers (no text)."
    )

    print(f"\n🔥 Prompt (trimmed):\n{prompt[:1000]}...\n")

    # 🧩 6️⃣ Call GPT
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
    print(f"💰 GPT Reply (trimmed):\n{reply[:800]}...\n")

    # 🧾 7️⃣ Log AI interaction
    log = AILog(
        user_message=request.message,
        detected_sport=sport,
        grok_context=context,
        ai_prompt=prompt,
        ai_response=reply,
    )
    db.add(log)
    db.commit()

    # 🧩 8️⃣ Parse JSON
    parsed = extract_json_block(reply)

    # 💾 9️⃣ Save parlay if valid JSON found
    saved_parlay = None
    if parsed:
        try:
            legs = parsed.get("parlay", [])
            total_odds = to_float(parsed.get("total_odds"))
            payout = to_float(parsed.get("potential_payout"))
            saved_parlay = save_parlay(db, sport, legs, total_odds, payout, reply)
            print("✅ Parlay saved successfully.")
        except Exception as e:
            print(f"⚠️ Could not parse/save parlay: {e}")

    # ✅ 10️⃣ Return full data
    return success_response(
        "AI parlay generated",
        {
            "raw_text": reply,
            "parsed_parlay": parsed,
            "saved": bool(saved_parlay)
        }
    )
