"""add bangumi_seasons table (many-to-many bangumi <-> season)

Revision ID: 011
Revises: 010
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bangumi_seasons',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('bangumi_id', sa.Integer(), sa.ForeignKey('bangumi.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('season', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('bangumi_id', 'year', 'season', name='uq_bangumi_season'),
    )


def downgrade() -> None:
    op.drop_table('bangumi_seasons')
