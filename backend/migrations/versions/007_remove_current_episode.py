"""remove current_episode from subscriptions table

Revision ID: 007
Revises: 006
Create Date: 2026-05-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('subscriptions', 'current_episode')


def downgrade() -> None:
    op.add_column('subscriptions', sa.Column('current_episode', sa.Integer(), nullable=False, server_default='0'))
    op.alter_column('subscriptions', 'current_episode', server_default=None)