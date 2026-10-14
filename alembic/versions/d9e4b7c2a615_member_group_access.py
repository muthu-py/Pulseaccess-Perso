"""member_group_access

Revision ID: d9e4b7c2a615
Revises: a6c8e0f24b13
Create Date: 2026-10-14 21:00:00.000000

Members joining a community's Telegram group:
  - communities.telegram_join_link: the shared join-request link
  - community_members: group_joined_at, group_left_at; status now
    PAID_NOT_JOINED / JOINED / LEFT / REMOVED
  - subscriptions.access_revoked_at: the expiry job handles each ended
    subscription once
"""
from alembic import op
import sqlalchemy as sa

revision = 'd9e4b7c2a615'
down_revision = 'a6c8e0f24b13'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'communities',
        sa.Column('telegram_join_link', sa.String(length=255), nullable=True),
    )

    op.add_column(
        'community_members',
        sa.Column('group_joined_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'community_members',
        sa.Column('group_left_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        'subscriptions',
        sa.Column('access_revoked_at', sa.DateTime(timezone=True), nullable=True),
    )
    # Subscriptions that ended before this release were never acted on;
    # treat them as handled so the first run doesn't remove people en masse.
    op.execute(
        "UPDATE subscriptions SET access_revoked_at = now() "
        "WHERE status IN ('expired', 'cancelled')"
    )


def downgrade() -> None:
    op.drop_column('subscriptions', 'access_revoked_at')
    op.drop_column('community_members', 'group_left_at')
    op.drop_column('community_members', 'group_joined_at')
    op.drop_column('communities', 'telegram_join_link')
