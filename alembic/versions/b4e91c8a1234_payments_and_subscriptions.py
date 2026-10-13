"""payments_and_subscriptions

Revision ID: b4e91c8a1234
Revises: 1c0f0a332e3f
Create Date: 2026-10-13 11:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b4e91c8a1234'
down_revision = '1c0f0a332e3f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Update subscriptions table ────────────────────────────────
    op.add_column(
        'subscriptions',
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))
    )
    op.add_column(
        'subscriptions',
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now() + interval '30 days'"))
    )
    op.add_column(
        'subscriptions',
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'subscriptions',
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))
    )
    op.add_column(
        'subscriptions',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('ix_subscriptions_member_id', 'subscriptions', ['member_id'], unique=False)
    op.create_index('ix_subscriptions_plan_id', 'subscriptions', ['plan_id'], unique=False)
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'], unique=False)

    # ── 2. Create payment_orders table ───────────────────────────────
    op.create_table(
        'payment_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('razorpay_order_id', sa.String(length=100), nullable=False),
        sa.Column('member_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount_paise', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='created'),
        sa.Column('receipt_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_payment_orders_razorpay_order_id', 'payment_orders', ['razorpay_order_id'], unique=True)
    op.create_index('ix_payment_orders_member_id', 'payment_orders', ['member_id'], unique=False)
    op.create_index('ix_payment_orders_plan_id', 'payment_orders', ['plan_id'], unique=False)
    op.create_index('ix_payment_orders_status', 'payment_orders', ['status'], unique=False)

    # ── 3. Update payment_events table ───────────────────────────────
    op.add_column(
        'payment_events',
        sa.Column('event_id', sa.String(length=100), nullable=True)
    )
    op.add_column(
        'payment_events',
        sa.Column('event_type', sa.String(length=50), nullable=False, server_default='unknown')
    )
    op.add_column(
        'payment_events',
        sa.Column('status', sa.String(length=30), nullable=False, server_default='processed')
    )
    op.add_column(
        'payment_events',
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))
    )
    op.create_index('ix_payment_events_event_id', 'payment_events', ['event_id'], unique=True)
    op.create_index('ix_payment_events_event_type', 'payment_events', ['event_type'], unique=False)


def downgrade() -> None:
    # Drop payment_events columns
    op.drop_index('ix_payment_events_event_type', table_name='payment_events')
    op.drop_index('ix_payment_events_event_id', table_name='payment_events')
    op.drop_column('payment_events', 'created_at')
    op.drop_column('payment_events', 'status')
    op.drop_column('payment_events', 'event_type')
    op.drop_column('payment_events', 'event_id')

    # Drop payment_orders table
    op.drop_index('ix_payment_orders_status', table_name='payment_orders')
    op.drop_index('ix_payment_orders_plan_id', table_name='payment_orders')
    op.drop_index('ix_payment_orders_member_id', table_name='payment_orders')
    op.drop_index('ix_payment_orders_razorpay_order_id', table_name='payment_orders')
    op.drop_table('payment_orders')

    # Drop subscriptions columns
    op.drop_index('ix_subscriptions_status', table_name='subscriptions')
    op.drop_index('ix_subscriptions_plan_id', table_name='subscriptions')
    op.drop_index('ix_subscriptions_member_id', table_name='subscriptions')
    op.drop_column('subscriptions', 'updated_at')
    op.drop_column('subscriptions', 'created_at')
    op.drop_column('subscriptions', 'cancelled_at')
    op.drop_column('subscriptions', 'ends_at')
    op.drop_column('subscriptions', 'starts_at')
