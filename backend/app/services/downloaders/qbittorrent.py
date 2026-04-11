from typing import Optional

import qbittorrentapi
from loguru import logger

from app.models.models import DownloaderConfig
from app.services.downloaders.base import BaseDownloader


class QBittorrentDownloader(BaseDownloader):
    def __init__(self, config: DownloaderConfig):
        super().__init__(config)
        self.client: Optional[qbittorrentapi.Client] = None

    async def _get_client(self) -> qbittorrentapi.Client:
        if self.client is None:
            self.client = qbittorrentapi.Client(
                host=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
            )
            self.client.auth_log_in()
        return self.client

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            client.app_version()
            return True
        except Exception as e:
            logger.error(f"qBittorrent connection test failed: {e}")
            raise Exception(f"qBittorrent 连接失败: {str(e)}")

    async def add_download(self, url: str, save_path: str = None) -> bool:
        try:
            client = await self._get_client()
            client.torrents_add(urls=url, save_path=save_path, category=self.config.token or "")
            return True
        except Exception as e:
            logger.error(f"qBittorrent add download failed: {e}")
            raise Exception(f"qBittorrent 添加下载失败: {str(e)}")

    async def get_download_status(self, download_id: str) -> dict:
        try:
            client = await self._get_client()
            torrents = client.torrents_info(torrent_hashes=download_id)

            if torrents:
                torrent = torrents[0]
                return {
                    "id": download_id,
                    "name": torrent.name,
                    "status": torrent.state,
                    "progress": torrent.progress * 100,
                    "download_speed": torrent.dlspeed,
                    "upload_speed": torrent.upspeed,
                }
            return {}
        except Exception as e:
            logger.error(f"qBittorrent get status failed: {e}")
            return {}

    async def remove_download(self, download_id: str, delete_files: bool = False) -> bool:
        try:
            client = await self._get_client()
            client.torrents_delete(torrent_hashes=download_id, delete_files=delete_files)
            return True
        except Exception as e:
            logger.error(f"qBittorrent remove download failed: {e}")
            return False

    async def get_downloads(self) -> list:
        try:
            client = await self._get_client()
            torrents = client.torrents_info()

            return [
                {
                    "id": t.hash,
                    "name": t.name,
                    "status": t.state,
                    "progress": t.progress * 100,
                    "download_speed": t.dlspeed,
                    "upload_speed": t.upspeed,
                }
                for t in torrents
            ]
        except Exception as e:
            logger.error(f"qBittorrent get downloads failed: {e}")
            return []
