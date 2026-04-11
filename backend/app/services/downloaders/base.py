from abc import ABC, abstractmethod
from typing import Optional

from app.models.models import DownloaderConfig


class BaseDownloader(ABC):
    def __init__(self, config: DownloaderConfig):
        self.config = config

    @abstractmethod
    async def test_connection(self) -> bool:
        pass

    @abstractmethod
    async def add_download(self, url: str, save_path: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    async def get_download_status(self, download_id: str) -> dict:
        pass

    @abstractmethod
    async def remove_download(self, download_id: str, delete_files: bool = False) -> bool:
        pass

    @abstractmethod
    async def get_downloads(self) -> list:
        pass
