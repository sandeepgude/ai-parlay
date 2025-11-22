from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.team_stats import TeamStats


def get_recent_team_stats(db: Session, sport: str, team: str, max_age_hours: int = 3):
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    return (
        db.query(TeamStats)
        .filter(
            TeamStats.sport == sport,
            TeamStats.team == team,
            TeamStats.fetched_at >= cutoff,
        )
        .first()
    )


def delete_team_stats(db: Session, sport: str, team: str):
    db.query(TeamStats).filter(
        TeamStats.sport == sport,
        TeamStats.team == team,
    ).delete()
    db.commit()


def save_team_stats(db: Session, sport: str, team: str, stats: dict):
    entry = TeamStats(
        sport=sport,
        team=team,
        stats=stats,
        fetched_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
