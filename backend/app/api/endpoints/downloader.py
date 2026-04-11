from typing import List
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from feedgen.feed import FeedGenerator

from app.api.endpoints.auth import get_current_active_user
from app.core.database import get_async_session
from app.models.models import DownloaderConfig, Episode, Subscription, User
from app.schemas import DownloaderConfigCreate, DownloaderConfigResponse, DownloaderConfigUpdate, DownloadRequest, DownloadResponse, MessageResponse
from app.services.downloaders import get_downloader

router = APIRouter()


@router.get("", response_model=List[DownloaderConfigResponse])
async def get_downloaders(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(select(DownloaderConfig).where(DownloaderConfig.user_id == current_user.id))
    return result.scalars().all()


@router.post("", response_model=DownloaderConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_downloader(
    downloader_create: DownloaderConfigCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    if downloader_create.is_default:
        existing_default = (await session.execute(
            select(DownloaderConfig)
            .where(DownloaderConfig.user_id == current_user.id, DownloaderConfig.is_default == True)
        )).scalars().all()
        
        for d in existing_default:
            d.is_default = False

    downloader = DownloaderConfig(
        user_id=current_user.id,
        name=downloader_create.name,
        downloader_type=downloader_create.downloader_type,
        host=downloader_create.host,
        port=downloader_create.port,
        username=downloader_create.username,
        password=downloader_create.password,
        rpc_url=downloader_create.rpc_url,
        token=downloader_create.token,
        is_default=downloader_create.is_default,
    )

    session.add(downloader)
    await session.commit()
    await session.refresh(downloader)

    return downloader


@router.put("/{downloader_id}", response_model=DownloaderConfigResponse)
async def update_downloader(
    downloader_id: int,
    downloader_update: DownloaderConfigUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(DownloaderConfig).where(
            DownloaderConfig.id == downloader_id, DownloaderConfig.user_id == current_user.id
        )
    )
    downloader = result.scalar_one_or_none()

    if not downloader:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="下载器不存在")

    update_data = downloader_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(downloader, field, value)

    await session.commit()
    await session.refresh(downloader)

    return downloader


@router.delete("/{downloader_id}", response_model=MessageResponse)
async def delete_downloader(
    downloader_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(DownloaderConfig).where(
            DownloaderConfig.id == downloader_id, DownloaderConfig.user_id == current_user.id
        )
    )
    downloader = result.scalar_one_or_none()

    if not downloader:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="下载器不存在")

    await session.delete(downloader)
    await session.commit()

    return MessageResponse(message="下载器删除成功")


@router.post("/{downloader_id}/test", response_model=MessageResponse)
async def test_downloader(
    downloader_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(DownloaderConfig).where(
            DownloaderConfig.id == downloader_id, DownloaderConfig.user_id == current_user.id
        )
    )
    downloader_config = result.scalar_one_or_none()

    if not downloader_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="下载器不存在")

    try:
        downloader = get_downloader(downloader_config)
        await downloader.test_connection()
        return MessageResponse(message="连接成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/download", response_model=DownloadResponse)
async def download_episodes(
    download_request: DownloadRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(select(Episode).where(Episode.id.in_(download_request.episode_ids)))
    episodes = result.scalars().all()

    if not episodes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到剧集")

    downloader_config = None
    if download_request.downloader_id:
        result = await session.execute(
            select(DownloaderConfig).where(
                DownloaderConfig.id == download_request.downloader_id, DownloaderConfig.user_id == current_user.id
            )
        )
        downloader_config = result.scalar_one_or_none()
    else:
        result = await session.execute(
            select(DownloaderConfig).where(
                DownloaderConfig.user_id == current_user.id, DownloaderConfig.is_default == True
            )
        )
        downloader_config = result.scalar_one_or_none()

    if downloader_config:
        try:
            downloader = get_downloader(downloader_config)
            added_count = 0
            for episode in episodes:
                if download_request.download_type == "torrent":
                    url = episode.torrent_url or episode.magnet_url
                else:
                    url = episode.magnet_url or episode.torrent_url
                if url:
                    await downloader.add_download(url, downloader_config.token)
                    added_count += 1
            return DownloadResponse(success=True, message=f"成功添加 {added_count} 个下载任务")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    else:
        if len(episodes) == 1:
            if download_request.download_type == "torrent":
                url = episodes[0].torrent_url or episodes[0].magnet_url
            else:
                url = episodes[0].magnet_url or episodes[0].torrent_url
            return DownloadResponse(
                success=True,
                message="获取下载链接成功",
                download_url=url,
            )
        else:
            urls = []
            for ep in episodes:
                if download_request.download_type == "torrent":
                    url = ep.torrent_url or ep.magnet_url
                else:
                    url = ep.magnet_url or ep.torrent_url
                if url:
                    urls.append(url)
            return DownloadResponse(success=True, message="获取下载链接成功", download_url="\n".join(urls))


@router.get("/rss/{subscription_id}")
async def get_rss_feed(
    subscription_id: int,
    token: str,
    session: AsyncSession = Depends(get_async_session),
):
    from fastapi.responses import Response
    from sqlalchemy.orm import selectinload
    from app.models.models import Bangumi
    
    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.bangumi).selectinload(Bangumi.episodes))
        .where(Subscription.id == subscription_id, Subscription.rss_token == token)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅不存在或token无效")

    episodes = subscription.bangumi.episodes

    fg = FeedGenerator()
    fg.id(f"bangumi-{subscription.bangumi.id}")
    fg.title(f"{subscription.bangumi.name} - BangumiHelper")
    fg.link(href="https://example.com", rel="alternate")
    fg.description("番剧订阅RSS")

    for ep in episodes:
        link = ep.magnet_url or ep.torrent_url or ""
        fe = fg.add_entry()
        fe.guid(f"episode-{ep.id}", permalink=False)
        fe.title(ep.title)
        
        description_parts = [f"第 {ep.episode_number} 集"]
        if ep.file_size:
            size_mb = ep.file_size / (1024 * 1024)
            description_parts.append(f"[{size_mb:.2f} MB]")
        if ep.subtitle_group:
            description_parts.append(f"字幕组: {ep.subtitle_group}")
        fe.description(" ".join(description_parts))
        
        if ep.torrent_url:
            fe.enclosure(
                url=ep.torrent_url,
                length=int(ep.file_size) if ep.file_size else 0,
                type="application/x-bittorrent"
            )
        elif ep.magnet_url:
            fe.link(href=ep.magnet_url)
        
        if ep.publish_time:
            from datetime import timezone
            if ep.publish_time.tzinfo is None:
                pubdate = ep.publish_time.replace(tzinfo=timezone.utc)
            else:
                pubdate = ep.publish_time
            fe.pubdate(pubdate)

    rss_content = fg.rss_str(pretty=True).decode("utf-8")

    return Response(content=rss_content, media_type="application/xml")


@router.post("/rss/{subscription_id}/regenerate")
async def regenerate_rss_token(
    subscription_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(Subscription).where(
            Subscription.id == subscription_id, 
            Subscription.user_id == current_user.id
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅不存在")

    subscription.rss_token = secrets.token_hex(32)
    await session.commit()

    return {"rss_token": subscription.rss_token}
