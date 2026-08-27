"""add episode check fields to bangumi

Revision ID: 010
Revises: 009
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('bangumi', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_episode_check_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('episode_check_interval', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('bangumi', schema=None) as batch_op:
        batch_op.drop_column('episode_check_interval')
        batch_op.drop_column('last_episode_check_at')
