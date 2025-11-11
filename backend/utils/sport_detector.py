# utils/sport_detector.py

def detect_sport(message: str):
    """
    Detects the sport mentioned in a user's message based on simple keyword matching.
    Later, this will be replaced with an NLP model or OpenAI call.
    """
    sports_keywords = {
        "nfl": ["football", "nfl", "broncos", "chiefs", "patriots", "eagles"],
        "nba": ["basketball", "nba", "lakers", "warriors", "celtics", "knicks"],
        "soccer": ["soccer", "premier", "arsenal", "barcelona", "madrid", "messi"],
        "mlb": ["baseball", "mlb", "yankees", "dodgers", "red sox"],
        "cricket": ["cricket", "ipl", "india", "australia", "england", "wickets"]
    }

    message = message.lower()
    for sport, keywords in sports_keywords.items():
        if any(word in message for word in keywords):
            return sport
    return "general"
