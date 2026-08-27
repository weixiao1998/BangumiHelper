import hashlib
from pathlib import Path

import aiohttp
from fastapi import HTTPException, status
from fastapi.responses import Response

from app.core.config import settings

# 封面本地缓存目录：{DATA_DIR}/covers
# 封面在本地缓存后由后端直接提供，并返回长效 Cache-Control，
# 避免每次进页面都从外部数据源(如蜜柑 CDN)重新下载。
CACHE_MAX_AGE = 60 * 60 * 24 * 7  # 7 天

# 封面域名跟随运行时配置 mikan_url 动态生成；下面仅记录同一站点可能出现的
# 域名别名，用于旧数据/域名切换时的兜底重试（优先级以 cover 里的实际域名为主）。
_COVER_DOMAIN_ALIASES = {
    "mikanime.tv": "mikanani.me",
}


def _candidate_cover_urls(cover_url: str) -> list[str]:
    # 优先使用 cover 里记录的域名（它来自 mikan_url 的当前配置），失败后才尝试别名兜底
    urls = [cover_url]
    for old, new in _COVER_DOMAIN_ALIASES.items():
        if old in cover_url:
            urls.append(cover_url.replace(old, new))
        if new in cover_url:
            urls.append(cover_url.replace(new, old))
    return urls


def _cover_cache_dir() -> Path:
    path = Path(settings.DATA_DIR) / "covers"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_paths(cover_url: str) -> tuple[Path, Path]:
    # 用封面 URL 的哈希作为文件名，URL 变化时自动重新缓存
    digest = hashlib.sha256(cover_url.encode("utf-8")).hexdigest()[:32]
    cache_dir = _cover_cache_dir()
    return cache_dir / f"{digest}.img", cache_dir / f"{digest}.type"


def _cache_headers() -> dict[str, str]:
    return {"Cache-Control": f"public, max-age={CACHE_MAX_AGE}, immutable"}


async def _download_cover(cover_url: str) -> tuple[bytes, str]:
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        async with session.get(cover_url) as resp:
            resp.raise_for_status()
            data = await resp.read()
            if not data:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="封面内容为空")
            content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            return data, content_type


async def get_cover_response(cover_url: str) -> Response:
    img_path, type_path = _cache_paths(cover_url)

    # 命中本地缓存，直接返回
    if img_path.exists():
        data = img_path.read_bytes()
        content_type = type_path.read_text().strip() if type_path.exists() else "image/jpeg"
        return Response(content=data, media_type=content_type, headers=_cache_headers())

    # 未命中，从外部源下载并落盘；若原始域名失效则按别名重试
    last_error: Exception | None = None
    for url in _candidate_cover_urls(cover_url):
        try:
            data, content_type = await _download_cover(url)
            break
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    else:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"封面下载失败: {last_error}",
        ) from last_error

    img_path.write_bytes(data)
    type_path.write_text(content_type)

    return Response(content=data, media_type=content_type, headers=_cache_headers())
