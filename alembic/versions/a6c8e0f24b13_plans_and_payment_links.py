"""plans_and_payment_links

Revision ID: a6c8e0f24b13
Revises: f1b3c5d7e902
Create Date: 2026-10-14 20:00:00.000000

Plans:
  - price (float rupees) → price_paise (integer paise)
  - add description, currency, is_active, created_at, updated_at
  - FK community_id → communities.id, UNIQUE(community_id, name)

Payment orders become "one purchase attempt" backed by a Razorpay Payment Link:
  - razorpay_order_id becomes nullable
  - add razorpay_payment_link_id (unique), payment_link_url, razorpay_payment_id,
    expires_at, paid_at
"""
from alembic import op
import sqlalchemy as sa

revision = 'a6c8e0f24b13'
down_revision = 'f1b3c5d7e902'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── plans ─────────────────────────────────────────────────────────
    op.add_column('plans', sa.Column('price_paise', sa.Integer(), nullable=True))
    op.execute('UPDATE plans SET price_paise = ROUND(price * 100)')
    op.alter_column('plans', 'price_paise', nullable=False)
    op.drop_column('plans', 'price')

    op.alter_column('plans', 'name', type_=sa.String(length=100), existing_nullable=False)
    op.add_column('plans', sa.Column('description', sa.String(length=500), nullable=True))
    op.add_column(
        'plans',
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='INR'),
    )
    op.add_column(
        'plans',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        'plans',
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column('plans', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        'fk_plans_community_id', 'plans', 'communities', ['community_id'], ['id'],
    )
    op.create_unique_constraint('uq_plans_community_name', 'plans', ['community_id', 'name'])
    op.create_index('ix_plans_community_id', 'plans', ['community_id'])

    # ── payment_orders ────────────────────────────────────────────────
    op.alter_column(
        'payment_orders', 'razorpay_order_id',
        existing_type=sa.String(length=100), nullable=True,
    )
    op.add_column(
        'payment_orders',
        sa.Column('razorpay_payment_link_id', sa.String(length=100), nullable=True),
    )
    op.add_column(
        'payment_orders',
        sa.Column('payment_link_url', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'payment_orders',
        sa.Column('razorpay_payment_id', sa.String(length=100), nullable=True),
    )
    op.add_column(
        'payment_orders',
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'payment_orders',
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'ix_payment_orders_razorpay_payment_link_id',
        'payment_orders',
        ['razorpay_payment_link_id'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_payment_orders_razorpay_payment_link_id', table_name='payment_orders')
    op.drop_column('payment_orders', 'paid_at')
    op.drop_column('payment_orders', 'expires_at')
    op.drop_column('payment_orders', 'razorpay_payment_id')
    op.drop_column('payment_orders', 'payment_link_url')
    op.drop_column('payment_orders', 'razorpay_payment_link_id')
    op.alter_column(
        'payment_orders', 'razorpay_order_id',
        existing_type=sa.String(length=100), nullable=False,
    )

    op.drop_index('ix_plans_community_id', table_name='plans')
    op.drop_constraint('uq_plans_community_name', 'plans', type_='unique')
    op.drop_constraint('fk_plans_community_id', 'plans', type_='foreignkey')
    op.drop_column('plans', 'updated_at')
    op.drop_column('plans', 'created_at')
    op.drop_column('plans', 'is_active')
    op.drop_column('plans', 'currency')
    op.drop_column('plans', 'description')
    op.alter_column('plans', 'name', type_=sa.String(), existing_nullable=False)
    op.add_column('plans', sa.Column('price', sa.Float(), nullable=True))
    op.execute('UPDATE plans SET price = price_paise / 100.0')
    op.alter_column('plans', 'price', nullable=False)
    op.drop_column('plans', 'price_paise')
