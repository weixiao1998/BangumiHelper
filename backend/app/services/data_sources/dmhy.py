import re
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.utils import beijing_to_utc
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


class DmhyDataSource(BaseDataSource):
    def __init__(self, proxy: str = ""):
        super().__init__(proxy)
        self.base_url = settings.DMHY_URL.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def _get_page(self, url: str, params: dict = None) -> str:
        async with self.session.get(url, params=params) as response:
            return await response.text()

    async def fetch_bangumi_calendar(self) -> list[BangumiInfo]:
        url = f"{self.base_url}/topics/list"
        html = await self._get_page(url, params={"sort_id": 2})
        soup = BeautifulSoup(html, "lxml")

        bangumi_map = {}

        for row in soup.select("tbody tr"):
            try:
                title_elem = row.select_one("a.title")
                if not title_elem:
                    continue

                title = title_elem.text.strip()
                href = title_elem.get("href", "")

                magnet_elem = row.select_one("a.magnet")
                if not magnet_elem:
                    continue

                date_elem = row.select_one("td:nth-child(1)")
                date_str = date_elem.text.strip() if date_elem else ""

                bangumi_name = self._extract_bangumi_name(title)
                if bangumi_name and bangumi_name not in bangumi_map:
                    bangumi_map[bangumi_name] = BangumiInfo(
                        name=bangumi_name,
                        keyword=bangumi_name,
                        update_time="Unknown",
                        data_source="dmhy",
                    )
            except Exception:
                continue

        return list(bangumi_map.values())

    def _extract_bangumi_name(self, title: str) -> str | None:
        patterns = [
            r"【([^】]+)】",
            r"\[([^\]]+)\]",
        ]

        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                name = match.group(1)
                name = re.sub(r"第?\d+.*$", "", name)
                name = re.sub(r"[\[\]【】]", "", name)
                return name.strip()

        return None

    async def fetch_single_bangumi(self, bangumi_id: str) -> BangumiInfo | None:
        episodes = await self.search_by_keyword(bangumi_id)
        if not episodes:
            return None

        return BangumiInfo(
            name=bangumi_id,
            keyword=bangumi_id,
            update_time="Unknown",
            data_source="dmhy",
            episodes=episodes,
        )

    async def fetch_episode_of_bangumi(self, bangumi_id: str, max_page: int = 3) -> list[EpisodeInfo]:
        return await self.search_by_keyword(bangumi_id, max_page)

    async def search_by_keyword(self, keyword: str, count: int = 3) -> list[EpisodeInfo]:
        episodes = []

        for page in range(1, count + 1):
            url = f"{self.base_url}/topics/list"
            html = await self._get_page(url, params={"keyword": keyword, "sort_id": 2, "page": page})
            soup = BeautifulSoup(html, "lxml")

            for row in soup.select("tbody tr"):
                try:
                    title_elem = row.select_one("a.title")
                    if not title_elem:
                        continue

                    title = title_elem.text.strip()

                    magnet_elem = row.select_one("a.magnet")
                    if not magnet_elem:
                        continue

                    magnet = magnet_elem.get("href", "")

                    date_elem = row.select_one("td:nth-child(1)")
                    publish_time = None
                    if date_elem:
                        date_str = date_elem.text.strip()
                        try:
                            dt = datetime.strptime(date_str, "%Y/%m/%d")
                            publish_time = beijing_to_utc(dt)
                        except ValueError:
                            pass

                    size_elem = row.select_one("td:nth-child(5)")
                    file_size = None
                    if size_elem:
                        size_str = size_elem.text.strip()
                        file_size = self._parse_file_size(size_str)

                    episodes.append(
                        EpisodeInfo(
                            title=title,
                            episode_number=parse_episode_number(title),
                            download_url=magnet,
                            magnet_url=magnet,
                            publish_time=publish_time,
                            file_size=file_size,
                        )
                    )
                except Exception:
                    continue

        return episodes

    def _parse_file_size(self, size_str: str) -> float | None:
        match = re.search(r"([\d.]+)\s*(MiB|GiB|MB|GB)", size_str, re.IGNORECASE)
        if match:
            size = float(match.group(1))
            unit = match.group(2).upper()

            if unit in ("GIB", "GB"):
                size *= 1024

            return size

        return None

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
