"""baseline schema

Revision ID: f61892921d14
Revises:
Create Date: 2025-11-05

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'f61892921d14'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('username', sa.String(), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
    )

    # bets table
    op.create_table(
        'bets',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('team_name', sa.String(), nullable=False, index=True),
        sa.Column('odds', sa.Float(), nullable=False),
        sa.Column('wager_amount', sa.Float(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
    )

def downgrade():
    op.drop_table('bets')
    op.drop_table('users')
