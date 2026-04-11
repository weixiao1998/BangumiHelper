"""init - create all tables

Revision ID: 001
Revises: 
Create Date: 2026-04-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(100), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    op.create_table(
        'subtitle_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('data_source', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id')
    )
    op.create_index(op.f('ix_subtitle_groups_id'), 'subtitle_groups', ['id'], unique=False)

    op.create_table(
        'bangumi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('keyword', sa.String(255), nullable=False),
        sa.Column('cover', sa.String(500), nullable=True),
        sa.Column('update_time', sa.String(10), nullable=True, default='Unknown'),
        sa.Column('status', sa.Integer(), nullable=True, default=0),
        sa.Column('data_source', sa.String(50), nullable=True, default='mikan'),
        sa.Column('subtitle_groups', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('keyword')
    )
    op.create_index(op.f('ix_bangumi_id'), 'bangumi', ['id'], unique=False)
    op.create_index(op.f('ix_bangumi_name'), 'bangumi', ['name'], unique=False)

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
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_downloader_configs_id'), 'downloader_configs', ['id'], unique=False)

    op.create_table(
        'bangumi_filters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('bangumi_name', sa.String(255), nullable=False),
        sa.Column('include_keywords', sa.Text(), nullable=True),
        sa.Column('exclude_keywords', sa.Text(), nullable=True),
        sa.Column('subtitle_groups', sa.Text(), nullable=True),
        sa.Column('regex_pattern', sa.String(500), nullable=True),
        sa.Column('min_episode', sa.Integer(), nullable=True),
        sa.Column('max_episode', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bangumi_filters_id'), 'bangumi_filters', ['id'], unique=False)

    op.create_table(
        'episodes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bangumi_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('episode_number', sa.Integer(), nullable=True, default=0),
        sa.Column('torrent_url', sa.Text(), nullable=True),
        sa.Column('magnet_url', sa.Text(), nullable=True),
        sa.Column('file_size', sa.Float(), nullable=True),
        sa.Column('subtitle_group', sa.String(100), nullable=True),
        sa.Column('publish_time', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['bangumi_id'], ['bangumi.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_episodes_bangumi_id'), 'episodes', ['bangumi_id'], unique=False)
    op.create_index(op.f('ix_episodes_id'), 'episodes', ['id'], unique=False)

    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('bangumi_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Integer(), nullable=True, default=1),
        sa.Column('current_episode', sa.Integer(), nullable=True, default=0),
        sa.Column('auto_download', sa.Boolean(), nullable=True, default=False),
        sa.Column('downloader_id', sa.Integer(), nullable=True),
        sa.Column('save_path', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['bangumi_id'], ['bangumi.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['downloader_id'], ['downloader_configs.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)

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
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_download_history_id'), 'download_history', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_download_history_id'), table_name='download_history')
    op.drop_table('download_history')

    op.drop_index(op.f('ix_subscriptions_id'), table_name='subscriptions')
    op.drop_table('subscriptions')

    op.drop_index(op.f('ix_episodes_id'), table_name='episodes')
    op.drop_index(op.f('ix_episodes_bangumi_id'), table_name='episodes')
    op.drop_table('episodes')

    op.drop_index(op.f('ix_bangumi_filters_id'), table_name='bangumi_filters')
    op.drop_table('bangumi_filters')

    op.drop_index(op.f('ix_downloader_configs_id'), table_name='downloader_configs')
    op.drop_table('downloader_configs')

    op.drop_index(op.f('ix_bangumi_id'), table_name='bangumi')
    op.drop_index(op.f('ix_bangumi_name'), table_name='bangumi')
    op.drop_table('bangumi')

    op.drop_index(op.f('ix_subtitle_groups_id'), table_name='subtitle_groups')
    op.drop_table('subtitle_groups')

    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
