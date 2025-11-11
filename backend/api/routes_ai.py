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

router = APIRouter(prefix="/ai", tags=["AI"])
client = OpenAI(api_key=OPENAI_API_KEY)

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
def chat(request: ChatRequest):
    """Simple chat endpoint for testing."""
    sport = detect_sport(request.message)
    prompt = (
        f"You are an AI parlay assistant.\n"
        f"User asked: '{request.message}'.\n"
        f"Detected sport: {sport}.\n"
        f"Give a concise betting insight or parlay idea."
    )

    print(f"\n🧠 Prompt sent to GPT:\n{prompt}\n")

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert AI sports assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=300,
        temperature=0.8,
    )

    reply = completion.choices[0].message.content.strip()
    print(f"💬 GPT Reply:\n{reply}\n")

    return success_response("AI response generated", {"reply": reply})


@router.post("/parlay")
async def parlay(request: ChatRequest, db: Session = Depends(get_db)):
    
    sport = detect_sport(request.message)
    tweets = get_trending_sport_tweets(sport)
    context = "\n".join(tweets)
    
    odds_result = await get_odds_data(db,sport)
    odds_data = odds_result["data"]


    prompt = (
        # f"Live chatter:\n{context}\n\n"
        f"User request: {request.message}\n"
        f"Sport detected: {sport}\n\n"
        f"{odds_data}\n\n"
        f"Generate a 2–3 leg parlay suggestion using the provided odds. "
        f"For each leg, explain reasoning, bookmaker, and implied value. "
        f"Return the result in concise JSON format with keys: parlay[], total_odds, reasoning."
    )

    print(f"\n🔥 Parlay Prompt:\n{prompt}\n")

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI sports betting assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=600,
        temperature=0.8,
    )

    reply = completion.choices[0].message.content.strip()
    print(f"💰 Parlay Suggestion:\n{reply}\n")

    log = AILog(
        user_message=request.message,
        detected_sport=sport,
        grok_context=context,
        ai_prompt=prompt,
        ai_response=reply,
    )
    db.add(log)
    db.commit()

    return success_response("AI parlay generated", {"reply": reply})
