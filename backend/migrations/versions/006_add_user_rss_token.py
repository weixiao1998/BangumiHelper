"""add rss_token to users table

Revision ID: 006
Revises: 005
Create Date: 2026-05-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('rss_token', sa.String(64), nullable=True))
    op.create_index(op.f('ix_users_rss_token'), 'users', ['rss_token'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_rss_token'), table_name='users')
    op.drop_column('users', 'rss_token')
