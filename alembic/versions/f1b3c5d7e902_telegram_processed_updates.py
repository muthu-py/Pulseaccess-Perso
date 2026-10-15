"""telegram_processed_updates

Revision ID: f1b3c5d7e902
Revises: c8d2e4f61a37
Create Date: 2026-10-14 18:00:00.000000

Webhook de-duplication: Telegram may deliver an update more than once.
"""
from alembic import op
import sqlalchemy as sa

revision = 'f1b3c5d7e902'
down_revision = 'c8d2e4f61a37'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'telegram_processed_updates',
        sa.Column('update_id', sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('telegram_processed_updates')
