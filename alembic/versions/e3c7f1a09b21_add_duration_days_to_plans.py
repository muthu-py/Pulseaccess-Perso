"""add_duration_days_to_plans

Revision ID: e3c7f1a09b21
Revises: b4e91c8a1234
Create Date: 2026-10-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'e3c7f1a09b21'
down_revision = 'b4e91c8a1234'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'plans',
        sa.Column('duration_days', sa.Integer(), nullable=False, server_default='30'),
    )


def downgrade() -> None:
    op.drop_column('plans', 'duration_days')
