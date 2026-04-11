from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class EpisodeInfo:
    title: str
    episode_number: int
    magnet_url: Optional[str] = None
    torrent_url: Optional[str] = None
    file_size: Optional[float] = None
    subtitle_group: Optional[str] = None
    publish_time: Optional[datetime] = None


@dataclass
class BangumiInfo:
    name: str
    keyword: str
    cover: Optional[str] = None
    update_time: str = "Unknown"
    status: int = 0
    data_source: str = "unknown"
    subtitle_groups: Optional[str] = None
    description: Optional[str] = None
    episodes: List[EpisodeInfo] = None

    def __post_init__(self):
        if self.episodes is None:
            self.episodes = []


@dataclass
class SubtitleGroupInfo:
    id: str
    name: str


class BaseDataSource(ABC):
    def __init__(self, proxy: str = ""):
        self.proxy = proxy

    @abstractmethod
    async def fetch_bangumi_calendar(self) -> List[BangumiInfo]:
        pass

    @abstractmethod
    async def fetch_single_bangumi(self, bangumi_id: str) -> Optional[BangumiInfo]:
        pass

    @abstractmethod
    async def fetch_episode_of_bangumi(self, bangumi_id: str, max_page: int = 3) -> List[EpisodeInfo]:
        pass

    @abstractmethod
    async def search_by_keyword(self, keyword: str, count: int = 3) -> List[EpisodeInfo]:
        pass

    async def fetch_and_save_bangumi(self, session: AsyncSession) -> List[BangumiInfo]:
        from app.models.models import Bangumi

        bangumi_list = await self.fetch_bangumi_calendar()

        for bangumi_info in bangumi_list:
            existing = await session.execute(
                Bangumi.__table__.select().where(Bangumi.keyword == bangumi_info.keyword)
            )
            if not existing.first():
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

        await session.commit()
        return bangumi_list
