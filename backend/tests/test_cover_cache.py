from io import BytesIO

import pytest
from PIL import Image

from app.services import cover_cache


def _make_cover(width: int, height: int) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), (180, 40, 60)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_resize_cover_downscales_to_requested_width():
    resized = cover_cache._resize_cover(_make_cover(1200, 1697), 320)

    assert resized is not None
    with Image.open(BytesIO(resized)) as img:
        assert img.size == (320, 453)


def test_resize_cover_skips_upscale():
    # 原图已经比目标窄时返回 None，由调用方直接返回原图
    assert cover_cache._resize_cover(_make_cover(200, 300), 320) is None


def test_resize_cover_rejects_invalid_image():
    with pytest.raises(cover_cache.HTTPException):
        cover_cache._resize_cover(b"not an image", 320)


async def test_get_cover_response_generates_and_caches_thumbnail(monkeypatch, tmp_path):
    monkeypatch.setattr(cover_cache.settings, "DATA_DIR", str(tmp_path))
    cover_url = "https://mikanani.me/images/Bangumi/202610/example.jpg"

    # 预置原图缓存，避免测试发起真实网络请求
    img_path, type_path = cover_cache._cache_paths(cover_url)
    img_path.write_bytes(_make_cover(1200, 1697))
    type_path.write_text("image/jpeg")

    response = await cover_cache.get_cover_response(cover_url, width=320)

    assert response.media_type == "image/jpeg"
    with Image.open(BytesIO(response.body)) as img:
        assert img.size == (320, 453)
    assert cover_cache._thumb_path(cover_url, 320).exists()

    # 第二次命中缩略图缓存，不再重复缩放
    cached = await cover_cache.get_cover_response(cover_url, width=320)
    assert cached.body == response.body
