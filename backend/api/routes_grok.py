from fastapi import APIRouter
from utils.grok_fetcher import get_trending_sport_tweets
from utils.response import success_response

router = APIRouter(prefix="/ai/grok", tags=["Grok"])

@router.get("/")
def get_grok_feed(sport: str = "nfl"):
    tweets = get_trending_sport_tweets(sport)
    return success_response("Fetched Grok data", {"tweets": tweets})
