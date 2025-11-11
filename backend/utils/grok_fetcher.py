def get_trending_sport_tweets(sport: str):
    """Mock version of Grok feed for development."""
    mock_data = {
        "nfl": [
            "Mahomes expected to start tonight 🏈",
            "Kelce cleared to play; line moving Chiefs -3.5",
            "Sharp bettors favoring Over 47.5 points",
        ],
        "nba": [
            "LeBron questionable vs Warriors 🤕",
            "Over 232.5 getting heavy action",
            "Public leaning Lakers -2",
        ],
        "mlb": [
            "Yankees favored -120 at home",
            "Total set at 8.5 runs",
            "Weather factors may favor unders",
        ],
    }
    return mock_data.get(sport.lower(), ["No live chatter found."])
