"""add player_stats and team_stats tables

Revision ID: b7a6f3b9e35d
Revises: 16627d17ac88
Create Date: 2025-02-08 05:18:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7a6f3b9e35d"
down_revision = "16627d17ac88"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_stats",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("sport", sa.String(), nullable=False, index=True),
        sa.Column("team", sa.String(), nullable=False, index=True),
        sa.Column("stats", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=True, index=True),
    )
    op.create_index(
        "idx_team_stats_sport_team",
        "team_stats",
        ["sport", "team"],
        unique=False,
    )

    op.create_table(
        "player_stats",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("sport", sa.String(), nullable=False, index=True),
        sa.Column("player", sa.String(), nullable=False, index=True),
        sa.Column("stats", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=True, index=True),
    )
    op.create_index(
        "idx_player_stats_sport_player",
        "player_stats",
        ["sport", "player"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_player_stats_sport_player", table_name="player_stats")
    op.drop_table("player_stats")
    op.drop_index("idx_team_stats_sport_team", table_name="team_stats")
    op.drop_table("team_stats")
