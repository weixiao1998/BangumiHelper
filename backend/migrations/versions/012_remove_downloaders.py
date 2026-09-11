"""remove server-side push to downloaders (RSS-only delivery)

背景：目标部署形态是公网共享实例，用户下载器位于各自 NAT 之后，服务器无法主动推送，
因此移除 downloader_configs / download_history 两张表，以及 subscriptions 上的
auto_download / downloader_id / save_path 三个从未被真正读取的字段。

Revision ID: 012
Revises: 011
Create Date: 2026-09-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_foreign_keys_for_columns(table: str, columns: set[str]) -> None:
    """删除引用了指定列的 FK。

    FK 名由数据库自动生成（如 MySQL 的 subscriptions_ibfk_2），无法写死，
    因此从 inspector 读取真实名字后再删，MySQL / PostgreSQL 均适用。
    """
    inspector = sa.inspect(op.get_bind())
    for fk in inspector.get_foreign_keys(table):
        if columns & set(fk.get('constrained_columns') or []):
            op.drop_constraint(fk['name'], table, type_='foreignkey')


def upgrade() -> None:
    # 1) 先删引用 downloader_configs 的字段与表（存在外键依赖顺序要求）
    _drop_foreign_keys_for_columns('subscriptions', {'downloader_id'})
    op.drop_column('subscriptions', 'downloader_id')
    op.drop_column('subscriptions', 'save_path')
    op.drop_column('subscriptions', 'auto_download')

    op.drop_table('download_history')
    op.drop_table('downloader_configs')


def downgrade() -> None:
    # 与 001_init 保持一致：不要在 Column 上用 index=True，索引统一显式创建，
    # 否则列级索引与 create_index 会重名（MySQL: Duplicate key name）。
    op.create_table(
        'downloader_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('downloader_type', sa.String(50), nullable=False),
        sa.Column('host', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('password', sa.String(255), nullable=True),
        sa.Column('rpc_url', sa.String(255), nullable=True),
        sa.Column('token', sa.String(255), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_downloader_configs_id'), 'downloader_configs', ['id'], unique=False)

    op.create_table(
        'download_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('episode_id', sa.Integer(), nullable=False),
        sa.Column('downloader_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['downloader_id'], ['downloader_configs.id'], ),
        sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_download_history_id'), 'download_history', ['id'], unique=False)

    op.add_column('subscriptions', sa.Column('auto_download', sa.Boolean(), nullable=True))
    op.add_column('subscriptions', sa.Column('save_path', sa.String(500), nullable=True))
    op.add_column(
        'subscriptions',
        sa.Column('downloader_id', sa.Integer(), sa.ForeignKey('downloader_configs.id'), nullable=True),
    )
