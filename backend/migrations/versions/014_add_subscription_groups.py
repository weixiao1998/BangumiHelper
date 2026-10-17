"""add subscription groups, drop global filters and per-subscription rss token

背景：订阅改为「用户 → 订阅组 → 番剧订阅」三级结构。组拥有一份默认过滤规则、
一条组 RSS 与独立 token；订阅的 inherit 模式改为使用组规则。

前置条件（重要）：本迁移按“存量订阅/规则数据已清空”设计，不做任何回填：
  DELETE FROM bangumi_filters;
  DELETE FROM subscriptions;
  DELETE FROM global_filters;

同时移除单订阅 RSS：删除 subscriptions.rss_token；旧 /downloaders/rss 兼容路径
也已从代码删除。用户级全部订阅 RSS 继续使用 users.rss_token。

Revision ID: 014
Revises: 013
Create Date: 2026-10-18

"""
import secrets
from datetime import UTC, datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_GROUP_NAME = '默认订阅组'


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def upgrade() -> None:
    # 1) 订阅组表
    op.create_table(
        'subscription_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('rss_token', sa.String(64), nullable=True),
        sa.Column('include_keywords', sa.Text(), nullable=True),
        sa.Column('exclude_keywords', sa.Text(), nullable=True),
        sa.Column('subtitle_groups', sa.Text(), nullable=True),
        sa.Column('language', sa.String(100), nullable=True),
        sa.Column('regex_pattern', sa.String(500), nullable=True),
        sa.Column('min_episode', sa.Integer(), nullable=True),
        sa.Column('max_episode', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_subscription_groups_user_name'),
    )
    op.create_index(op.f('ix_subscription_groups_id'), 'subscription_groups', ['id'], unique=False)
    op.create_index(
        op.f('ix_subscription_groups_rss_token'), 'subscription_groups', ['rss_token'], unique=False
    )

    # 2) 为已有用户初始化一个空的默认订阅组（不复制任何规则数据）
    conn = op.get_bind()
    user_ids = [row[0] for row in conn.execute(sa.text('SELECT id FROM users')).fetchall()]
    now = _now()
    for user_id in user_ids:
        conn.execute(
            sa.text(
                'INSERT INTO subscription_groups '
                '(user_id, name, description, status, rss_token, created_at, updated_at) '
                'VALUES (:user_id, :name, NULL, 1, :token, :now, :now)'
            ),
            {
                'user_id': user_id,
                'name': DEFAULT_GROUP_NAME,
                'token': secrets.token_hex(32),
                'now': now,
            },
        )

    # 3) 订阅增加 group_id（前置条件保证表为空）
    op.add_column('subscriptions', sa.Column('group_id', sa.Integer(), nullable=False))
    op.create_index(op.f('ix_subscriptions_group_id'), 'subscriptions', ['group_id'], unique=False)
    op.create_foreign_key(
        'fk_subscriptions_group_id',
        'subscriptions',
        'subscription_groups',
        ['group_id'],
        ['id'],
        ondelete='CASCADE',
    )

    # 4) 移除单订阅 RSS token
    op.drop_index('ix_subscriptions_rss_token', table_name='subscriptions')
    op.drop_column('subscriptions', 'rss_token')

    # 5) 移除用户级全局过滤
    op.drop_index('ix_global_filters_id', table_name='global_filters')
    op.drop_table('global_filters')


def downgrade() -> None:
    # 只恢复表结构，不恢复数据（有损回滚）
    op.create_table(
        'global_filters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('include_keywords', sa.Text(), nullable=True),
        sa.Column('exclude_keywords', sa.Text(), nullable=True),
        sa.Column('subtitle_groups', sa.Text(), nullable=True),
        sa.Column('language', sa.String(100), nullable=True),
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

    op.add_column('subscriptions', sa.Column('rss_token', sa.String(64), nullable=True))
    op.create_index(op.f('ix_subscriptions_rss_token'), 'subscriptions', ['rss_token'], unique=False)

    op.drop_constraint('fk_subscriptions_group_id', 'subscriptions', type_='foreignkey')
    op.drop_index(op.f('ix_subscriptions_group_id'), table_name='subscriptions')
    op.drop_column('subscriptions', 'group_id')

    op.drop_index(op.f('ix_subscription_groups_rss_token'), table_name='subscription_groups')
    op.drop_index(op.f('ix_subscription_groups_id'), table_name='subscription_groups')
    op.drop_table('subscription_groups')
