from app.models.models import DownloaderConfig
from app.services.downloaders.aria2 import Aria2Downloader
from app.services.downloaders.base import BaseDownloader
from app.services.downloaders.qbittorrent import QBittorrentDownloader
from app.services.downloaders.transmission import TransmissionDownloader

_downloaders = {
    "aria2": Aria2Downloader,
    "qbittorrent": QBittorrentDownloader,
    "transmission": TransmissionDownloader,
}


def get_downloader(config: DownloaderConfig) -> BaseDownloader:
    if config.downloader_type not in _downloaders:
        raise ValueError(f"Unknown downloader type: {config.downloader_type}")

    return _downloaders[config.downloader_type](config)


def list_downloaders() -> list[str]:
    return list(_downloaders.keys())
