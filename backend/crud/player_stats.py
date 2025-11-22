from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.player_stats import PlayerStats


def get_recent_player_stats(db: Session, sport: str, player: str, max_age_hours: int = 3):
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    return (
        db.query(PlayerStats)
        .filter(
            PlayerStats.sport == sport,
            PlayerStats.player == player,
            PlayerStats.fetched_at >= cutoff,
        )
        .first()
    )


def delete_player_stats(db: Session, sport: str, player: str):
    db.query(PlayerStats).filter(
        PlayerStats.sport == sport,
        PlayerStats.player == player,
    ).delete()
    db.commit()


def save_player_stats(db: Session, sport: str, player: str, stats: dict):
    entry = PlayerStats(
        sport=sport,
        player=player,
        stats=stats,
        fetched_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
