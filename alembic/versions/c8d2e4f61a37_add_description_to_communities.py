"""add_description_to_communities

Revision ID: c8d2e4f61a37
Revises: c7d2e5f8a901
Create Date: 2026-10-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'c8d2e4f61a37'
down_revision = 'c7d2e5f8a901'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'communities',
        sa.Column('description', sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('communities', 'description')
