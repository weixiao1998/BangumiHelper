"""add invite codes table

Revision ID: 002
Revises: 001
Create Date: 2026-04-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'invite_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('used_by', sa.Integer(), nullable=True),
        sa.Column('is_used', sa.Boolean(), nullable=True, default=False),
        sa.Column('max_uses', sa.Integer(), nullable=True, default=1),
        sa.Column('current_uses', sa.Integer(), nullable=True, default=0),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['used_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_invite_codes_id'), 'invite_codes', ['id'], unique=False)
    op.create_index(op.f('ix_invite_codes_code'), 'invite_codes', ['code'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_invite_codes_code'), table_name='invite_codes')
    op.drop_index(op.f('ix_invite_codes_id'), table_name='invite_codes')
    op.drop_table('invite_codes')
