"""add subscription_id to bangumi_filters

Revision ID: 004
Revises: 003
Create Date: 2026-04-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('bangumi_filters', schema=None) as batch_op:
        batch_op.add_column(sa.Column('subscription_id', sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE bangumi_filters
        SET subscription_id = (
            SELECT subscriptions.id
            FROM subscriptions
            JOIN bangumi ON subscriptions.bangumi_id = bangumi.id
            WHERE subscriptions.user_id = bangumi_filters.user_id
              AND bangumi.name = bangumi_filters.bangumi_name
            LIMIT 1
        )
        """
    )

    with op.batch_alter_table('bangumi_filters', schema=None) as batch_op:
        batch_op.alter_column('subscription_id', nullable=False)
        batch_op.create_unique_constraint('uq_bangumi_filters_subscription_id', ['subscription_id'])
        batch_op.create_foreign_key(
            'fk_bangumi_filters_subscription_id',
            'subscriptions',
            ['subscription_id'], ['id'],
            ondelete='CASCADE',
        )


def downgrade() -> None:
    with op.batch_alter_table('bangumi_filters', schema=None) as batch_op:
        batch_op.drop_constraint('fk_bangumi_filters_subscription_id', type_='foreignkey')
        batch_op.drop_constraint('uq_bangumi_filters_subscription_id', type_='unique')
        batch_op.drop_column('subscription_id')
