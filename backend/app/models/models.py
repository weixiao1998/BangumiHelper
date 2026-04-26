from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.utils import utc_now


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    downloaders: Mapped[List["DownloaderConfig"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    filters: Mapped[List["BangumiFilter"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Bangumi(Base):
    __tablename__ = "bangumi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    cover: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    update_time: Mapped[str] = mapped_column(String(10), default="Unknown")
    status: Mapped[int] = mapped_column(Integer, default=0)
    data_source: Mapped[str] = mapped_column(String(50), default="mikan")
    subtitle_groups: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    episodes: Mapped[List["Episode"]] = relationship(back_populates="bangumi", cascade="all, delete-orphan")
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="bangumi", cascade="all, delete-orphan")


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bangumi_id: Mapped[int] = mapped_column(Integer, ForeignKey("bangumi.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    episode_number: Mapped[int] = mapped_column(Integer, default=0)
    torrent_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    magnet_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    subtitle_group: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    publish_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    bangumi: Mapped["Bangumi"] = relationship(back_populates="episodes")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bangumi_id: Mapped[int] = mapped_column(Integer, ForeignKey("bangumi.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[int] = mapped_column(Integer, default=1)
    current_episode: Mapped[int] = mapped_column(Integer, default=0)
    auto_download: Mapped[bool] = mapped_column(Boolean, default=False)
    downloader_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("downloader_configs.id"), nullable=True)
    save_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    rss_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    bangumi: Mapped["Bangumi"] = relationship(back_populates="subscriptions")
    downloader: Mapped[Optional["DownloaderConfig"]] = relationship(back_populates="subscriptions")


class BangumiFilter(Base):
    __tablename__ = "bangumi_filters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bangumi_name: Mapped[str] = mapped_column(String(255), nullable=False)
    include_keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exclude_keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subtitle_groups: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    regex_pattern: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    min_episode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_episode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship(back_populates="filters")


class DownloaderConfig(Base):
    __tablename__ = "downloader_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    downloader_type: Mapped[str] = mapped_column(String(50), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rpc_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship(back_populates="downloaders")
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="downloader")


class DownloadHistory(Base):
    __tablename__ = "download_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    episode_id: Mapped[int] = mapped_column(Integer, ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False)
    downloader_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("downloader_configs.id"), nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class SubtitleGroup(Base):
    __tablename__ = "subtitle_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_source: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    used_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    current_uses: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    user: Mapped[Optional["User"]] = relationship(foreign_keys=[used_by])
