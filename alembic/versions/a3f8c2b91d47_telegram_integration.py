"""telegram_integration

Revision ID: a3f8c2b91d47
Revises: 7895ed7e2224
Create Date: 2026-07-27 08:00:00.000000

Schema changes (Doc 03):
  1. Rename communities.telegram_channel_id → telegram_chat_id
  2. Add communities.telegram_connection_status (VARCHAR, default NOT_CONNECTED)
  3. Add communities.telegram_connected_at (TIMESTAMP WITH TIME ZONE, nullable)
  4. Create telegram_operations table (persistent async operation queue)
  5. Create all required indexes
"""
from alembic import op
import sqlalchemy as sa


revision = 'a3f8c2b91d47'
down_revision = '7895ed7e2224'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Step 1: Rename telegram_channel_id → telegram_chat_id ────────
    op.alter_column(
        'communities',
        'telegram_channel_id',
        new_column_name='telegram_chat_id',
        existing_type=sa.String(),
        existing_nullable=True,
    )

    # ── Step 2: Add telegram_connection_status ────────────────────────
    op.add_column(
        'communities',
        sa.Column(
            'telegram_connection_status',
            sa.String(length=20),
            nullable=False,
            server_default='NOT_CONNECTED',
        ),
    )

    # ── Step 3: Add telegram_connected_at ────────────────────────────
    op.add_column(
        'communities',
        sa.Column(
            'telegram_connected_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # ── Step 4: Make telegram_chat_id nullable and add unique index ───
    op.alter_column(
        'communities',
        'telegram_chat_id',
        existing_type=sa.String(),
        nullable=True,
    )
    op.create_index(
        'ix_communities_telegram_chat_id',
        'communities',
        ['telegram_chat_id'],
        unique=True,
    )

    # ── Step 5: Create telegram_operations table ──────────────────────
    op.create_table(
        'telegram_operations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('operation_type', sa.String(length=50), nullable=False),
        sa.Column('community_id', sa.UUID(), nullable=False),
        sa.Column('member_id', sa.UUID(), nullable=True),
        sa.Column(
            'status',
            sa.String(length=20),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['community_id'], ['communities.id'], ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['member_id'], ['members.id'], ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── Step 6: Create indexes on telegram_operations ─────────────────
    op.create_index(
        'ix_telegram_operations_status',
        'telegram_operations',
        ['status'],
        unique=False,
    )
    op.create_index(
        'ix_telegram_operations_scheduled_at',
        'telegram_operations',
        ['scheduled_at'],
        unique=False,
    )
    op.create_index(
        'ix_telegram_operations_community_id',
        'telegram_operations',
        ['community_id'],
        unique=False,
    )
    op.create_index(
        'ix_telegram_operations_member_id',
        'telegram_operations',
        ['member_id'],
        unique=False,
    )


def downgrade() -> None:
    # ── Remove telegram_operations table and its indexes ─────────────
    op.drop_index('ix_telegram_operations_member_id', table_name='telegram_operations')
    op.drop_index('ix_telegram_operations_community_id', table_name='telegram_operations')
    op.drop_index('ix_telegram_operations_scheduled_at', table_name='telegram_operations')
    op.drop_index('ix_telegram_operations_status', table_name='telegram_operations')
    op.drop_table('telegram_operations')

    # ── Remove telegram_chat_id unique index ──────────────────────────
    op.drop_index('ix_communities_telegram_chat_id', table_name='communities')

    # ── Remove added community columns ────────────────────────────────
    op.drop_column('communities', 'telegram_connected_at')
    op.drop_column('communities', 'telegram_connection_status')

    # ── Rename back telegram_chat_id → telegram_channel_id ───────────
    op.alter_column(
        'communities',
        'telegram_chat_id',
        new_column_name='telegram_channel_id',
        existing_type=sa.String(),
        existing_nullable=True,
    )
