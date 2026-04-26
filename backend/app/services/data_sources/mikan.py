import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.utils import beijing_to_utc
from app.services.data_sources.base import BaseDataSource, BangumiInfo, EpisodeInfo

CN_WEEK_MAP = {
    "星期日": "Sun",
    "星期一": "Mon",
    "星期二": "Tue",
    "星期三": "Wed",
    "星期四": "Thu",
    "星期五": "Fri",
    "星期六": "Sat",
    "OVA": "Unknown",
}

DAY_OF_WEEK_MAP = {
    0: "星期日",
    1: "星期一",
    2: "星期二",
    3: "星期三",
    4: "星期四",
    5: "星期五",
    6: "星期六",
    8: "OVA",
}


def parse_episode_number(title: str) -> int:
    patterns = [
        r"\[(\d{1,3})(?:v\d)?(?:\s*END)?\]",
        r"第(\d{1,3})[话集]",
        r"EP?(\d{1,3})",
        r"(\d{1,3})\s*(?:END|Fin)",
        r"S\d+E(\d{1,3})",
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


class MikanDataSource(BaseDataSource):
    def __init__(self, proxy: str = ""):
        super().__init__(proxy)
        self.base_url = settings.MIKAN_URL.rstrip("/")
        self.login_url = f"{self.base_url}/Account/Login"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            proxy=proxy if proxy else None,
            follow_redirects=True,
        )

    async def _login(self):
        if not settings.MIKAN_USERNAME or not settings.MIKAN_PASSWORD:
            return

        response = await self.client.get(self.login_url)
        soup = BeautifulSoup(response.text, "lxml")
        token_input = soup.find("input", attrs={"name": "__RequestVerificationToken"})

        if not token_input:
            return

        token = token_input.get("value")

        await self.client.post(
            self.login_url,
            data={
                "UserName": settings.MIKAN_USERNAME,
                "Password": settings.MIKAN_PASSWORD,
                "__RequestVerificationToken": token,
            },
            headers={"Referer": self.login_url},
        )

    async def _get_page(self, url: str, params: dict = None) -> str:
        response = await self.client.get(url, params=params)
        if "退出" not in response.text and settings.MIKAN_USERNAME:
            await self._login()
            response = await self.client.get(url, params=params)
        return response.text

    async def fetch_bangumi_calendar(self) -> List[BangumiInfo]:
        html = await self._get_page(self.base_url)
        soup = BeautifulSoup(html, "lxml")

        bangumi_list = []

        for day_num in range(0, 9):
            if day_num == 7:
                continue

            day_container = soup.find("div", attrs={"class": "sk-bangumi", "data-dayofweek": str(day_num)})
            if not day_container:
                continue

            weekday = CN_WEEK_MAP.get(DAY_OF_WEEK_MAP.get(day_num, "Unknown"), "Unknown")

            for item in day_container.find_all("li"):
                link = item.find("a")
                span = item.find("span")

                if link and span:
                    name = link.get("title", "")
                    href = link.get("href", "")
                    bangumi_id = href.split("/")[-1] if href else ""
                    cover = urljoin(self.base_url, span.get("data-src", ""))

                    if name and bangumi_id:
                        bangumi_list.append(
                            BangumiInfo(
                                name=name,
                                keyword=bangumi_id,
                                cover=cover.split("?")[0],
                                update_time=weekday,
                                data_source="mikan",
                            )
                        )

        return bangumi_list

    async def fetch_single_bangumi(self, bangumi_id: str) -> Optional[BangumiInfo]:
        url = f"{self.base_url}/Home/Bangumi/{bangumi_id}"
        html = await self._get_page(url)
        soup = BeautifulSoup(html, "lxml")

        left_container = soup.select_one("div.pull-left.leftbar-container")
        if not left_container:
            return None

        title_elem = left_container.find("p", class_="bangumi-title")
        if not title_elem:
            return None

        name = title_elem.text.strip()

        day_elem = title_elem.find_next_sibling("p", class_="bangumi-info")
        update_time = "Unknown"
        if day_elem:
            day_text = day_elem.text.strip()
            for cn_day, en_day in CN_WEEK_MAP.items():
                if cn_day in day_text:
                    update_time = en_day
                    break

        subtitle_groups = []
        nav = soup.find("div", class_="leftbar-nav")
        if nav:
            for li in nav.find_all("li"):
                a = li.find("a")
                if a:
                    sub_id = a.get("data-anchor", "")[1:]
                    sub_name = a.text.strip()
                    if sub_id and sub_name:
                        subtitle_groups.append(f"{sub_id}:{sub_name}")

        subtitle_group_map = {}
        for sg in subtitle_groups:
            if ":" in sg:
                sub_id, sub_name = sg.split(":", 1)
                subtitle_group_map[sub_id] = sub_name

        episodes = await self._parse_episodes(html, bangumi_id, subtitle_group_map)

        return BangumiInfo(
            name=name,
            keyword=bangumi_id,
            update_time=update_time,
            data_source="mikan",
            subtitle_groups=",".join(subtitle_groups) if subtitle_groups else None,
            episodes=episodes,
        )

    async def _parse_episodes(self, html: str, bangumi_id: str, subtitle_group_map: dict = None) -> List[EpisodeInfo]:
        soup = BeautifulSoup(html, "lxml")
        episodes = []

        container = soup.find("div", class_="central-container")
        if not container:
            return episodes

        episode_containers = {}
        for tag in container.contents:
            if not hasattr(tag, "attrs"):
                continue

            subtitle_id = tag.attrs.get("id")
            if subtitle_id:
                episode_containers[subtitle_id] = tag.find_next_sibling("div", class_="episode-table")

        for subtitle_id, table in episode_containers.items():
            if not table:
                continue

            for tr in table.find_all("tr")[1:]:
                try:
                    title_elem = tr.find("a", class_="magnet-link-wrap")
                    magnet_elem = tr.find("a", class_="magnet-link")

                    if not title_elem or not magnet_elem:
                        continue

                    title = title_elem.text.strip()
                    magnet = magnet_elem.get("data-clipboard-text", "")

                    torrent_url = None
                    for a in tr.find_all("a"):
                        href = a.get("href", "")
                        if href and href.endswith(".torrent"):
                            torrent_url = urljoin(self.base_url, href)
                            break

                    tds = tr.find_all("td")
                    publish_time = None
                    if len(tds) >= 4:
                        time_str = tds[3].text.strip()
                        try:
                            dt = datetime.strptime(time_str, "%Y/%m/%d %H:%M")
                            publish_time = beijing_to_utc(dt)
                        except ValueError:
                            pass

                    subtitle_group_name = subtitle_id
                    if subtitle_group_map and subtitle_id in subtitle_group_map:
                        subtitle_group_name = subtitle_group_map[subtitle_id]

                    episodes.append(
                        EpisodeInfo(
                            title=title,
                            episode_number=parse_episode_number(title),
                            torrent_url=torrent_url,
                            magnet_url=magnet,
                            subtitle_group=subtitle_group_name,
                            publish_time=publish_time,
                        )
                    )
                except Exception:
                    continue

        return episodes

    async def fetch_episode_of_bangumi(self, bangumi_id: str, max_page: int = 3) -> List[EpisodeInfo]:
        bangumi = await self.fetch_single_bangumi(bangumi_id)
        return bangumi.episodes if bangumi else []

    async def search_by_keyword(self, keyword: str, count: int = 3) -> List[EpisodeInfo]:
        url = f"{self.base_url}/Home/Search"
        html = await self._get_page(url, params={"searchstr": keyword})
        soup = BeautifulSoup(html, "lxml")

        episodes = []

        for tr in soup.find_all("tr", attrs={"class": "js-search-results-row"}):
            try:
                title_elem = tr.find("a", class_="magnet-link-wrap")
                magnet_elem = tr.find("a", class_="magnet-link")

                if not title_elem or not magnet_elem:
                    continue

                title = title_elem.text.strip()
                magnet = magnet_elem.get("data-clipboard-text", "")

                torrent_url = None
                for a in tr.find_all("a"):
                    href = a.get("href", "")
                    if href and href.endswith(".torrent"):
                        torrent_url = urljoin(self.base_url, href)
                        break

                tds = tr.find_all("td")
                publish_time = None
                if len(tds) >= 4:
                    time_str = tds[3].text.strip()
                    try:
                        dt = datetime.strptime(time_str, "%Y/%m/%d %H:%M")
                        publish_time = beijing_to_utc(dt)
                    except ValueError:
                        pass

                episodes.append(
                    EpisodeInfo(
                        title=title,
                        episode_number=parse_episode_number(title),
                        torrent_url=torrent_url,
                        magnet_url=magnet,
                        publish_time=publish_time,
                    )
                )
            except Exception:
                continue

        return episodes

    async def close(self):
        await self.client.aclose()
