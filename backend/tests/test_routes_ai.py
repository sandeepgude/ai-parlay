import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from main import app
import api.routes_ai as routes_ai


client = TestClient(app)


def _sample_odds():
    return [
        {
            "home_team": "Orlando Magic",
            "away_team": "Los Angeles Lakers",
            "sport": "nba",
            "bookmaker": "TestBook",
            "market": "h2h",
            "odds": [
                {"name": "Orlando Magic", "price": 1.9},
                {"name": "Los Angeles Lakers", "price": 1.9},
            ],
            "commence_time": None,
        }
    ]


def _fake_completion_non_stream():
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(
                        {
                            "parlay": [{"team": "Orlando Magic", "market": "h2h", "selection": "Orlando ML", "odds": 1.9, "confidence": "high", "reason": "test"}],
                            "total_odds": 1.9,
                            "potential_payout": "Stake x 1.9",
                            "reasoning": "test reasoning",
                        }
                    )
                )
            )
        ]
    )


class _FakeChunk:
    def __init__(self, text):
        self.choices = [SimpleNamespace(delta=SimpleNamespace(content=text))]


def _fake_stream_chunks():
    # one chunk with the full JSON body
    payload = json.dumps(
        {
            "parlay": [{"team": "Magic", "market": "h2h", "selection": "Magic ML", "odds": 1.9, "confidence": "high", "reason": "test"}],
            "total_odds": 1.9,
            "potential_payout": "Stake x 1.9",
            "reasoning": "test",
        }
    )
    return [_FakeChunk(payload)]


def test_parlay_endpoint(monkeypatch):
    # Patch odds + stats to avoid network
    monkeypatch.setattr(routes_ai, "get_odds_data", lambda db, sport: {"source": "api", "data": _sample_odds()})
    monkeypatch.setattr(routes_ai, "get_team_stats", lambda sport, team, db=None, max_age_hours=3: {"team": team})
    monkeypatch.setattr(routes_ai, "get_player_stats", lambda sport, name, db=None, max_age_hours=3: {"player": name})
    monkeypatch.setattr(routes_ai.client.chat.completions, "create", lambda **kwargs: _fake_completion_non_stream())

    resp = client.post("/api/v1/ai/parlay", json={"message": "Best NBA parlay"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["parsed_parlay"] is not None
    assert data["parsed_parlay"]["parlay"]


def test_chat_stream_endpoint(monkeypatch):
    # Patch odds + stats
    monkeypatch.setattr(routes_ai, "get_odds_data", lambda db, sport: {"source": "api", "data": _sample_odds()})
    monkeypatch.setattr(routes_ai, "get_team_stats", lambda sport, team, db=None, max_age_hours=3: {"team": team})
    monkeypatch.setattr(routes_ai, "get_player_stats", lambda sport, name, db=None, max_age_hours=3: {"player": name})

    # streaming call returns iterable of chunks
    monkeypatch.setattr(
        routes_ai.client.chat.completions,
        "create",
        lambda stream=False, **kwargs: _fake_stream_chunks() if stream else _fake_completion_non_stream(),
    )

    resp = client.post("/api/v1/ai/chat-stream", json={"message": "Best NBA parlay"})
    assert resp.status_code == 200
    body = resp.text
    assert "[[FINAL_JSON]]" in body
    start = body.index("[[FINAL_JSON]]") + len("[[FINAL_JSON]]")
    end = body.index("[[/FINAL_JSON]]")
    final = json.loads(body[start:end])
    assert final["parsed_parlay"] is not None
    assert final["parsed_parlay"]["parlay"]
