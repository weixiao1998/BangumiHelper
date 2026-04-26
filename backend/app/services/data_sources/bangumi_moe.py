import re
from datetime import datetime
from urllib.parse import urljoin

import aiohttp

from app.core.config import settings
from app.services.data_sources.base import BangumiInfo, BaseDataSource, EpisodeInfo


def parse_episode_number(title: str) -> int:
    patterns = [
        r"\[(\d{1,3})(?:v\d)?(?:\s*END)?\]",
        r"第(\d{1,3})[话集]",
        r"EP?(\d{1,3})",
        r"(\d{1,3})\s*(?:END|Fin)",
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return int(match.group(1))

    numbers = re.findall(r"\d{2,3}", title)
    if numbers:
        for num in numbers:
            n = int(num)
            if 1 <= n <= 1000:
                return n

    return 0


class BangumiMoeDataSource(BaseDataSource):
    def __init__(self, proxy: str = ""):
        super().__init__(proxy)
        self.base_url = settings.BANGUMI_MOE_URL.rstrip("/")
        self.api_url = f"{self.base_url}/api"
        self._session: aiohttp.ClientSession | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def _get_json(self, url: str, json_data: dict = None) -> dict:
        if json_data:
            async with self.session.post(url, json=json_data) as response:
                return await response.json()
        else:
            async with self.session.get(url) as response:
                return await response.json()

    async def fetch_bangumi_calendar(self) -> list[BangumiInfo]:
        url = f"{self.api_url}/bangumi/current"

        try:
            data = await self._get_json(url)

            bangumi_list = []
            for item in data.get("bangumi", []):
                name = item.get("name", "")
                bangumi_id = item.get("_id", "")
                cover = item.get("cover", "")

                if cover and not cover.startswith("http"):
                    cover = urljoin(self.base_url, cover)

                update_time = "Unknown"
                if "showOn" in item:
                    update_time = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][item["showOn"] % 7]

                if name and bangumi_id:
                    bangumi_list.append(
                        BangumiInfo(
                            name=name,
                            keyword=bangumi_id,
                            cover=cover,
                            update_time=update_time,
                            data_source="bangumi_moe",
                        )
                    )

            return bangumi_list
        except Exception:
            return []

    async def fetch_single_bangumi(self, bangumi_id: str) -> BangumiInfo | None:
        url = f"{self.api_url}/bangumi/{bangumi_id}"

        try:
            data = await self._get_json(url)

            name = data.get("name", "")
            cover = data.get("cover", "")

            if cover and not cover.startswith("http"):
                cover = urljoin(self.base_url, cover)

            episodes = await self.fetch_episode_of_bangumi(bangumi_id)

            return BangumiInfo(
                name=name,
                keyword=bangumi_id,
                cover=cover,
                update_time="Unknown",
                data_source="bangumi_moe",
                episodes=episodes,
            )
        except Exception:
            return None

    async def fetch_episode_of_bangumi(self, bangumi_id: str, max_page: int = 3) -> list[EpisodeInfo]:
        url = f"{self.api_url}/torrent/search"
        episodes = []

        try:
            data = await self._get_json(
                url,
                json_data={
                    "bangumi": bangumi_id,
                    "p": 1,
                },
            )

            for item in data.get("torrents", []):
                title = item.get("title", "")
                magnet = item.get("magnet", "")
                torrent_url = item.get("torrent", "")

                if torrent_url and not torrent_url.startswith("http"):
                    torrent_url = urljoin(self.base_url, torrent_url)

                publish_time = None
                if "date" in item:
                    try:
                        publish_time = datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                file_size = item.get("size")

                episodes.append(
                    EpisodeInfo(
                        title=title,
                        episode_number=parse_episode_number(title),
                        download_url=magnet or torrent_url,
                        magnet_url=magnet,
                        torrent_url=torrent_url,
                        publish_time=publish_time,
                        file_size=float(file_size) if file_size else None,
                    )
                )
        except Exception:
            pass

        return episodes

    async def search_by_keyword(self, keyword: str, count: int = 3) -> list[EpisodeInfo]:
        url = f"{self.api_url}/torrent/search"
        episodes = []

        try:
            data = await self._get_json(
                url,
                json_data={
                    "query": keyword,
                    "p": 1,
                },
            )

            for item in data.get("torrents", []):
                title = item.get("title", "")
                magnet = item.get("magnet", "")
                torrent_url = item.get("torrent", "")

                if torrent_url and not torrent_url.startswith("http"):
                    torrent_url = urljoin(self.base_url, torrent_url)

                publish_time = None
                if "date" in item:
                    try:
                        publish_time = datetime.fromisoformat(item["date"].replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                file_size = item.get("size")

                episodes.append(
                    EpisodeInfo(
                        title=title,
                        episode_number=parse_episode_number(title),
                        download_url=magnet or torrent_url,
                        magnet_url=magnet,
                        torrent_url=torrent_url,
                        publish_time=publish_time,
                        file_size=float(file_size) if file_size else None,
                    )
                )
        except Exception:
            pass

        return episodes

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
