from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class EpisodeInfo:
    title: str
    episode_number: int
    magnet_url: str | None = None
    torrent_url: str | None = None
    file_size: float | None = None
    subtitle_group: str | None = None
    publish_time: datetime | None = None


@dataclass
class BangumiInfo:
    name: str
    keyword: str
    cover: str | None = None
    update_time: str = "Unknown"
    status: int = 0
    data_source: str = "unknown"
    subtitle_groups: str | None = None
    description: str | None = None
    year: int | None = None
    season: str | None = None
    episodes: list[EpisodeInfo] = None

    def __post_init__(self):
        if self.episodes is None:
            self.episodes = []


@dataclass
class SubtitleGroupInfo:
    id: str
    name: str


class BaseDataSource(ABC):
    def __init__(self, cfg):
        self.cfg = cfg
        self.proxy = cfg.proxy

    @abstractmethod
    async def fetch_bangumi_calendar(self, year: int | None = None, season: str | None = None) -> list[BangumiInfo]:
        pass

    @abstractmethod
    async def fetch_single_bangumi(self, bangumi_id: str) -> BangumiInfo | None:
        pass

    @abstractmethod
    async def fetch_episode_of_bangumi(self, bangumi_id: str, max_page: int = 3) -> list[EpisodeInfo]:
        pass

    @abstractmethod
    async def search_by_keyword(self, keyword: str, count: int = 3) -> list[EpisodeInfo]:
        pass

    async def fetch_and_save_bangumi(
        self, session: AsyncSession, year: int | None = None, season: str | None = None
    ) -> list[BangumiInfo]:
        from sqlalchemy import select

        from app.models.models import Bangumi, BangumiSeason

        bangumi_list = await self.fetch_bangumi_calendar(year=year, season=season)

        for bangumi_info in bangumi_list:
            existing = await session.execute(select(Bangumi).where(Bangumi.keyword == bangumi_info.keyword))
            bangumi = existing.scalar_one_or_none()
            if bangumi is None:
                bangumi = Bangumi(
                    name=bangumi_info.name,
                    keyword=bangumi_info.keyword,
                    cover=bangumi_info.cover,
                    update_time=bangumi_info.update_time,
                    status=bangumi_info.status,
                    data_source=bangumi_info.data_source,
                    subtitle_groups=bangumi_info.subtitle_groups,
                    description=bangumi_info.description,
                )
                session.add(bangumi)
                await session.flush()  # 取得 bangumi.id
            else:
                # 重新抓取时刷新已有番剧元信息：周几/类别可能已修正（如 OVA/剧场版），标题/封面也可能变化。
                bangumi.update_time = bangumi_info.update_time
                if bangumi_info.name:
                    bangumi.name = bangumi_info.name
                if bangumi_info.cover:
                    bangumi.cover = bangumi_info.cover

            # 记录番剧 ↔ 季度 的多对多关联（同季度已存在则不重复写入）
            if bangumi_info.year is not None and bangumi_info.season is not None:
                season_exists = await session.execute(
                    select(BangumiSeason).where(
                        BangumiSeason.bangumi_id == bangumi.id,
                        BangumiSeason.year == bangumi_info.year,
                        BangumiSeason.season == bangumi_info.season,
                    )
                )
                if not season_exists.scalar_one_or_none():
                    session.add(
                        BangumiSeason(bangumi_id=bangumi.id, year=bangumi_info.year, season=bangumi_info.season)
                    )

        await session.commit()
        return bangumi_list
