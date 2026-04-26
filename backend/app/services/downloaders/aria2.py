import aiohttp
from loguru import logger

from app.models.models import DownloaderConfig
from app.services.downloaders.base import BaseDownloader


class Aria2Downloader(BaseDownloader):
    def __init__(self, config: DownloaderConfig):
        super().__init__(config)
        self.rpc_url = config.rpc_url or f"http://{config.host}:{config.port}/rpc"
        self.token = config.token or ""
        self._session: aiohttp.ClientSession | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def _call_rpc(self, method: str, params: list = None) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": "bangumi-helper",
            "method": method,
            "params": [f"token:{self.token}"] + (params or []),
        }

        async with self.session.post(self.rpc_url, json=payload) as response:
            return await response.json()

    async def test_connection(self) -> bool:
        try:
            result = await self._call_rpc("aria2.getVersion")
            if "result" in result:
                return True
            raise Exception(f"RPC 返回错误: {result.get('error', '未知错误')}")
        except Exception as e:
            logger.error(f"Aria2 connection test failed: {e}")
            raise Exception(f"Aria2 连接失败: {str(e)}")

    async def add_download(self, url: str, save_path: str = None) -> bool:
        try:
            options = {}
            if save_path:
                options["dir"] = save_path

            result = await self._call_rpc("aria2.addUri", [[url], options])
            if "result" in result:
                return True
            raise Exception(f"RPC 返回错误: {result.get('error', '未知错误')}")
        except Exception as e:
            logger.error(f"Aria2 add download failed: {e}")
            raise Exception(f"Aria2 添加下载失败: {str(e)}")

    async def get_download_status(self, download_id: str) -> dict:
        try:
            result = await self._call_rpc("aria2.tellStatus", [download_id])
            if "result" in result:
                status = result["result"]
                return {
                    "id": download_id,
                    "status": status.get("status", "unknown"),
                    "progress": float(status.get("completedLength", 0)) / float(status.get("totalLength", 1)) * 100,
                    "download_speed": status.get("downloadSpeed", 0),
                }
            return {}
        except Exception as e:
            logger.error(f"Aria2 get status failed: {e}")
            return {}

    async def remove_download(self, download_id: str, delete_files: bool = False) -> bool:
        try:
            if delete_files:
                result = await self._call_rpc("aria2.removeDownloadResult", [download_id])
            else:
                result = await self._call_rpc("aria2.remove", [download_id])
            return "result" in result
        except Exception as e:
            logger.error(f"Aria2 remove download failed: {e}")
            return False

    async def get_downloads(self) -> list:
        try:
            active = await self._call_rpc("aria2.tellActive")
            waiting = await self._call_rpc("aria2.tellWaiting", [0, 100])
            stopped = await self._call_rpc("aria2.tellStopped", [0, 100])

            downloads = []
            for result in [active, waiting, stopped]:
                if "result" in result:
                    downloads.extend(result["result"])

            return downloads
        except Exception as e:
            logger.error(f"Aria2 get downloads failed: {e}")
            return []

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
