"""connect_telegram

Revision ID: c7d2e5f8a901
Revises: e3c7f1a09b21
Create Date: 2026-10-14 10:00:00.000000

Schema changes for the shared "Connect Telegram" flow:
  1. creators.phone (nullable, unique) — needed before a creator connects Telegram
  2. members becomes one account per person: name, phone, email, is_active,
     created_at. community_id and telegram_user_id are removed.
     NOTE: the members table must be empty (new NOT NULL columns, no defaults).
  3. community_members — members ↔ communities (many-to-many)
  4. member_login_otps — member passwordless login
  5. telegram_accounts — verified Telegram account per creator / member
  6. telegram_link_tokens — one-time codes behind the "Connect Telegram" button
"""
from alembic import op
import sqlalchemy as sa


revision = 'c7d2e5f8a901'
down_revision = 'e3c7f1a09b21'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Step 1: creators.phone ────────────────────────────────────────
    op.add_column('creators', sa.Column('phone', sa.String(length=20), nullable=True))
    op.create_unique_constraint('uq_creators_phone', 'creators', ['phone'])

    # ── Step 2: reshape members ───────────────────────────────────────
    op.drop_column('members', 'community_id')
    op.drop_column('members', 'telegram_user_id')
    op.add_column('members', sa.Column('name', sa.String(length=255), nullable=False))
    op.add_column('members', sa.Column('phone', sa.String(length=20), nullable=False))
    op.add_column('members', sa.Column('email', sa.String(length=255), nullable=False))
    op.add_column(
        'members',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        'members',
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_unique_constraint('uq_members_phone', 'members', ['phone'])
    op.create_unique_constraint('uq_members_email', 'members', ['email'])

    # ── Step 3: community_members ─────────────────────────────────────
    op.create_table(
        'community_members',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('member_id', sa.UUID(), nullable=False),
        sa.Column('community_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='JOINED'),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['community_id'], ['communities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'member_id', 'community_id', name='uq_community_members_member_community',
        ),
    )
    op.create_index(
        'ix_community_members_community_id', 'community_members', ['community_id'],
    )

    # ── Step 4: member_login_otps ─────────────────────────────────────
    op.create_table(
        'member_login_otps',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('member_id', sa.UUID(), nullable=False),
        sa.Column('otp_hash', sa.String(length=255), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_member_login_otps_member_id', 'member_login_otps', ['member_id'])

    # ── Step 5: telegram_accounts ─────────────────────────────────────
    op.create_table(
        'telegram_accounts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('owner_type', sa.String(length=20), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('telegram_user_id', sa.String(length=32), nullable=False),
        sa.Column('telegram_username', sa.String(length=64), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('linked_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_type', 'owner_id', name='uq_telegram_accounts_owner'),
        sa.UniqueConstraint(
            'owner_type', 'telegram_user_id',
            name='uq_telegram_accounts_owner_type_tg_user',
        ),
    )
    op.create_index(
        'ix_telegram_accounts_telegram_user_id', 'telegram_accounts', ['telegram_user_id'],
    )

    # ── Step 6: telegram_link_tokens ──────────────────────────────────
    op.create_table(
        'telegram_link_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('owner_type', sa.String(length=20), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('telegram_user_id', sa.String(length=32), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index(
        'ix_telegram_link_tokens_telegram_user_id',
        'telegram_link_tokens',
        ['telegram_user_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_telegram_link_tokens_telegram_user_id', table_name='telegram_link_tokens')
    op.drop_table('telegram_link_tokens')
    op.drop_index('ix_telegram_accounts_telegram_user_id', table_name='telegram_accounts')
    op.drop_table('telegram_accounts')
    op.drop_index('ix_member_login_otps_member_id', table_name='member_login_otps')
    op.drop_table('member_login_otps')
    op.drop_index('ix_community_members_community_id', table_name='community_members')
    op.drop_table('community_members')

    # members back to the 3-column shape (data in the new columns is lost)
    op.drop_constraint('uq_members_email', 'members', type_='unique')
    op.drop_constraint('uq_members_phone', 'members', type_='unique')
    op.drop_column('members', 'created_at')
    op.drop_column('members', 'is_active')
    op.drop_column('members', 'email')
    op.drop_column('members', 'phone')
    op.drop_column('members', 'name')
    op.add_column('members', sa.Column('telegram_user_id', sa.String(), nullable=True))
    op.add_column('members', sa.Column('community_id', sa.Uuid(), nullable=True))

    op.drop_constraint('uq_creators_phone', 'creators', type_='unique')
    op.drop_column('creators', 'phone')
