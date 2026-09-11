"""filter mode: global default vs per-subscription, and language on global filter

背景：此前「全局过滤器」与「订阅过滤器」是硬 AND 叠加，用户无法为单个订阅开例外，
且详情页复制的判定逻辑漏掉了全局规则。现改为：一个订阅只有一份生效规则，
由 subscriptions.filter_mode 决定（inherit=全局默认规则 / custom=订阅自身规则）。

存量兼容：已经有订阅级规则的订阅回填为 custom，保证其行为不变（不会突然改用全局规则）。

Revision ID: 013
Revises: 012
Create Date: 2026-09-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'subscriptions',
        sa.Column('filter_mode', sa.String(10), nullable=False, server_default='inherit'),
    )
    # GlobalFilter 与 BangumiFilter 字段对齐（补 language，原先全局规则无法按语言筛选）
    op.add_column('global_filters', sa.Column('language', sa.String(100), nullable=True))

    # 已有订阅级规则的订阅 → custom，保持重构前“自己的规则生效”的行为
    op.execute(
        "UPDATE subscriptions SET filter_mode = 'custom' "
        "WHERE id IN (SELECT subscription_id FROM bangumi_filters)"
    )


def downgrade() -> None:
    op.drop_column('global_filters', 'language')
    op.drop_column('subscriptions', 'filter_mode')
