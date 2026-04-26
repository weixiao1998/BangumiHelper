
import transmission_rpc
from loguru import logger

from app.models.models import DownloaderConfig
from app.services.downloaders.base import BaseDownloader


class TransmissionDownloader(BaseDownloader):
    def __init__(self, config: DownloaderConfig):
        super().__init__(config)
        self.client: transmission_rpc.Client | None = None

    async def _get_client(self) -> transmission_rpc.Client:
        if self.client is None:
            self.client = transmission_rpc.Client(
                host=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
            )
        return self.client

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            client.session_stats()
            return True
        except Exception as e:
            logger.error(f"Transmission connection test failed: {e}")
            raise Exception(f"Transmission 连接失败: {str(e)}")

    async def add_download(self, url: str, save_path: str = None) -> bool:
        try:
            client = await self._get_client()
            client.add_torrent(url, download_dir=save_path)
            return True
        except Exception as e:
            logger.error(f"Transmission add download failed: {e}")
            raise Exception(f"Transmission 添加下载失败: {str(e)}")

    async def get_download_status(self, download_id: str) -> dict:
        try:
            client = await self._get_client()
            torrent = client.get_torrent(int(download_id))

            return {
                "id": download_id,
                "name": torrent.name,
                "status": torrent.status,
                "progress": torrent.progress * 100,
                "download_speed": torrent.rate_download,
                "upload_speed": torrent.rate_upload,
            }
        except Exception as e:
            logger.error(f"Transmission get status failed: {e}")
            return {}

    async def remove_download(self, download_id: str, delete_files: bool = False) -> bool:
        try:
            client = await self._get_client()
            client.remove_torrent(int(download_id), delete_data=delete_files)
            return True
        except Exception as e:
            logger.error(f"Transmission remove download failed: {e}")
            return False

    async def get_downloads(self) -> list:
        try:
            client = await self._get_client()
            torrents = client.get_torrents()

            return [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "status": t.status,
                    "progress": t.progress * 100,
                    "download_speed": t.rate_download,
                    "upload_speed": t.rate_upload,
                }
                for t in torrents
            ]
        except Exception as e:
            logger.error(f"Transmission get downloads failed: {e}")
            return []
