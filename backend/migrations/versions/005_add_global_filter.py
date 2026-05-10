"""add global_filters table

Revision ID: 005
Revises: 004
Create Date: 2026-04-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'global_filters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('include_keywords', sa.Text(), nullable=True),
        sa.Column('exclude_keywords', sa.Text(), nullable=True),
        sa.Column('subtitle_groups', sa.Text(), nullable=True),
        sa.Column('regex_pattern', sa.String(500), nullable=True),
        sa.Column('min_episode', sa.Integer(), nullable=True),
        sa.Column('max_episode', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_global_filters_id'), 'global_filters', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_global_filters_id'), table_name='global_filters')
    op.drop_table('global_filters')
