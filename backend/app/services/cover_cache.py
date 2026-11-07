import hashlib
from asyncio import to_thread
from io import BytesIO
from pathlib import Path

import aiohttp
from fastapi import HTTPException, status
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings

# 封面本地缓存目录：{DATA_DIR}/covers
# 封面在本地缓存后由后端直接提供，并返回长效 Cache-Control，
# 避免每次进页面都从外部数据源(如蜜柑 CDN)重新下载。
CACHE_MAX_AGE = 60 * 60 * 24 * 7  # 7 天

# 列表/卡片页只需要小图：原图通常有 1200px 宽，直接交给浏览器从 1200px 缩到
# 200px 左右时，细线条会被采样成很硬的深色描边（看起来像「黑线」）。
# 这里按请求宽度生成缩略图并缓存，让浏览器只做小幅缩放，同时减少流量。
COVER_THUMB_MAX_WIDTH = 1600
COVER_THUMB_QUALITY = 82

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


def _thumb_path(cover_url: str, width: int) -> Path:
    digest = hashlib.sha256(cover_url.encode("utf-8")).hexdigest()[:32]
    return _cover_cache_dir() / f"{digest}_{width}.jpg"


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


async def _load_original(cover_url: str) -> tuple[bytes, str]:
    """返回缓存的原图；缓存未命中时从外部源下载并落盘。"""
    img_path, type_path = _cache_paths(cover_url)

    # 命中本地缓存，直接返回
    if img_path.exists():
        data = img_path.read_bytes()
        content_type = type_path.read_text().strip() if type_path.exists() else "image/jpeg"
        return data, content_type

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

    return data, content_type


def _resize_cover(data: bytes, width: int) -> bytes | None:
    """把封面缩放到指定宽度；原图本身不大于目标宽度时返回 None。

    使用 BOX（面积平均）重采样：Lanczos 之类的高锐度算法会在深色细线两侧
    产生振铃/暗晕，正是卡片小图上「黑描边」的来源之一。
    """
    try:
        with Image.open(BytesIO(data)) as img:
            if img.width <= width:
                return None

            # JPEG 可以按 1/2、1/4 比例解码，先 draft 再 load 可大幅减少解码耗时
            img.draft("RGB", (width, width * 2))
            img = ImageOps.exif_transpose(img)

            if img.mode in ("RGBA", "LA", "P"):
                rgba = img.convert("RGBA")
                img = Image.new("RGB", rgba.size, (255, 255, 255))
                img.paste(rgba, mask=rgba.getchannel("A"))
            else:
                img = img.convert("RGB")

            height = max(1, round(img.height * width / img.width))
            resized = img.resize((width, height), Image.Resampling.BOX)

            buffer = BytesIO()
            resized.save(buffer, format="JPEG", quality=COVER_THUMB_QUALITY, optimize=True, progressive=True)
            return buffer.getvalue()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="封面图片无法解析") from exc


async def get_cover_response(cover_url: str, width: int | None = None) -> Response:
    """返回封面响应；指定 width 时返回按该宽度缩放后的 JPEG 缩略图。"""
    data, content_type = await _load_original(cover_url)

    if width is None:
        return Response(content=data, media_type=content_type, headers=_cache_headers())

    width = max(64, min(width, COVER_THUMB_MAX_WIDTH))
    thumb_path = _thumb_path(cover_url, width)

    if thumb_path.exists():
        return Response(content=thumb_path.read_bytes(), media_type="image/jpeg", headers=_cache_headers())

    # 解码/缩放是 CPU 操作，放到线程池避免阻塞事件循环
    try:
        thumb = await to_thread(_resize_cover, data, width)
    except HTTPException:
        # Pillow 解析不了的格式（例如浏览器支持但 Pillow 不支持的图片）退回原图，避免卡片裂图
        thumb = None
    if thumb is None:
        # 原图已经比目标宽度小（或无法缩放），直接返回原图，避免无意义放大
        return Response(content=data, media_type=content_type, headers=_cache_headers())

    thumb_path.write_bytes(thumb)
    return Response(content=thumb, media_type="image/jpeg", headers=_cache_headers())
