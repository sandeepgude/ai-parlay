from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from models.game_odds import GameOdds
from models.game import Game
from models.team_market import TeamMarket
from models.player_prop import PlayerProp


# --------------------------------------------------------------------
# Legacy helpers (game_odds table)
# --------------------------------------------------------------------
def save_odds(db: Session, sport: str, home_team: str, away_team: str, bookmaker: str, market: str, odds_data: dict):
    entry = GameOdds(
        sport=sport,
        home_team=home_team,
        away_team=away_team,
        bookmaker=bookmaker,
        market=market,
        odds_data=odds_data,
        fetched_at=datetime.utcnow()
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_recent_odds(db: Session, sport: str, max_age_hours: int = 6):
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    return db.query(GameOdds).filter(GameOdds.sport == sport, GameOdds.fetched_at >= cutoff).all()


# --------------------------------------------------------------------
# New helpers (games + team_markets + player_props)
# --------------------------------------------------------------------
def upsert_game(db: Session, sport: str, event_id: str, home_team: str, away_team: str, commence_time: str | None, source: str | None):
    game = (
        db.query(Game)
        .filter(Game.sport == sport, Game.event_id == event_id)
        .one_or_none()
    )
    if game:
        game.home_team = home_team
        game.away_team = away_team
        game.commence_time = commence_time
        game.source = source or game.source
        game.fetched_at = datetime.utcnow()
    else:
        game = Game(
            sport=sport,
            event_id=event_id,
            home_team=home_team,
            away_team=away_team,
            commence_time=commence_time,
            source=source,
            fetched_at=datetime.utcnow(),
        )
        db.add(game)
    db.commit()
    db.refresh(game)
    return game


def upsert_team_market(db: Session, game_id: int, sport: str, bookmaker: str, market: str, odds_data, commence_time: str | None):
    entry = (
        db.query(TeamMarket)
        .filter(
            TeamMarket.game_id == game_id,
            TeamMarket.bookmaker == bookmaker,
            TeamMarket.market == market,
        )
        .one_or_none()
    )
    if entry:
        entry.odds_data = odds_data
        entry.commence_time = commence_time
        entry.fetched_at = datetime.utcnow()
    else:
        entry = TeamMarket(
            game_id=game_id,
            sport=sport,
            bookmaker=bookmaker,
            market=market,
            odds_data=odds_data,
            commence_time=commence_time,
            fetched_at=datetime.utcnow(),
        )
        db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def upsert_player_prop(
    db: Session,
    game_id: int,
    sport: str,
    bookmaker: str,
    player: str,
    stat_type: str,
    side: str | None,
    line: float | None,
    price: int | None,
):
    entry = (
        db.query(PlayerProp)
        .filter(
            PlayerProp.game_id == game_id,
            PlayerProp.bookmaker == bookmaker,
            PlayerProp.player == player,
            PlayerProp.stat_type == stat_type,
            PlayerProp.side == side,
        )
        .one_or_none()
    )
    if entry:
        entry.line = line
        entry.price = price
        entry.fetched_at = datetime.utcnow()
    else:
        entry = PlayerProp(
            game_id=game_id,
            sport=sport,
            bookmaker=bookmaker,
            player=player,
            stat_type=stat_type,
            side=side,
            line=line,
            price=price,
            fetched_at=datetime.utcnow(),
        )
        db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_recent_team_markets(db: Session, sport: str, max_age_hours: int = 6):
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    return (
        db.query(TeamMarket, Game)
        .join(Game, Game.id == TeamMarket.game_id)
        .filter(TeamMarket.sport == sport, TeamMarket.fetched_at >= cutoff)
        .all()
    )


def get_recent_player_props(db: Session, sport: str, max_age_hours: int = 6):
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    return (
        db.query(PlayerProp, Game)
        .join(Game, Game.id == PlayerProp.game_id)
        .filter(PlayerProp.sport == sport, PlayerProp.fetched_at >= cutoff)
        .all()
    )
