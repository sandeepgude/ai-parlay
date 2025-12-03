"""add games and props tables

Revision ID: 9b1f4b2d9d6b
Revises: b7a6f3b9e35d
Create Date: 2024-11-21 07:20:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9b1f4b2d9d6b"
down_revision = "b7a6f3b9e35d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sport", sa.String(), nullable=False, index=True),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("home_team", sa.String(), nullable=False),
        sa.Column("away_team", sa.String(), nullable=False),
        sa.Column("commence_time", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("sport", "event_id", name="uq_game_sport_event"),
    )

    op.create_table(
        "team_markets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sport", sa.String(), nullable=False, index=True),
        sa.Column("bookmaker", sa.String(), nullable=False),
        sa.Column("market", sa.String(), nullable=False),
        sa.Column("odds_data", sa.JSON(), nullable=False),
        sa.Column("commence_time", sa.String(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("game_id", "bookmaker", "market", name="uq_team_market"),
    )

    op.create_table(
        "player_props",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sport", sa.String(), nullable=False, index=True),
        sa.Column("bookmaker", sa.String(), nullable=False),
        sa.Column("player", sa.String(), nullable=False),
        sa.Column("stat_type", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=True),
        sa.Column("line", sa.Float(), nullable=True),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("game_id", "bookmaker", "player", "stat_type", "side", name="uq_player_prop"),
    )


def downgrade() -> None:
    op.drop_table("player_props")
    op.drop_table("team_markets")
    op.drop_table("games")
