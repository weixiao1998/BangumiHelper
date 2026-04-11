"""add rss_token to subscriptions

Revision ID: 003
Revises: 002
Create Date: 2026-04-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('subscriptions', sa.Column('rss_token', sa.String(64), nullable=True))
    op.create_index(op.f('ix_subscriptions_rss_token'), 'subscriptions', ['rss_token'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_subscriptions_rss_token'), table_name='subscriptions')
    op.drop_column('subscriptions', 'rss_token')
