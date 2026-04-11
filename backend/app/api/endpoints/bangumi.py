from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_active_user
from app.core.database import get_async_session
from app.models.models import Bangumi, Episode, Subscription, User
from app.schemas import BangumiListResponse, BangumiResponse, CalendarResponse, MessageResponse, SearchResult
from app.services.data_sources import get_data_source

router = APIRouter()


@router.get("/calendar", response_model=List[CalendarResponse])
async def get_calendar(
    data_source: str = Query(default="mikan", description="数据源"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(select(Bangumi).where(Bangumi.data_source == data_source))
    db_bangumi_list = result.scalars().all()

    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.bangumi))
        .where(Subscription.user_id == current_user.id)
    )
    subscriptions = {sub.bangumi.name: sub for sub in result.scalars().all()}

    weekday_map: Dict[str, List[BangumiListResponse]] = {}
    for bangumi in db_bangumi_list:
        sub = subscriptions.get(bangumi.name)
        bangumi_response = BangumiListResponse(
            id=bangumi.id,
            name=bangumi.name,
            keyword=bangumi.keyword,
            cover=bangumi.cover,
            update_time=bangumi.update_time,
            status=bangumi.status,
            data_source=bangumi.data_source,
            subtitle_groups=bangumi.subtitle_groups,
            description=bangumi.description,
            is_subscribed=sub is not None,
            current_episode=sub.current_episode if sub else 0,
        )

        weekday = bangumi.update_time.lower()
        if weekday not in weekday_map:
            weekday_map[weekday] = []
        weekday_map[weekday].append(bangumi_response)

    calendar = [CalendarResponse(weekday=day, bangumi_list=bangumis) for day, bangumis in weekday_map.items()]

    return calendar


@router.get("/search", response_model=List[SearchResult])
async def search_bangumi(
    keyword: str = Query(..., description="搜索关键词"),
    data_source: str = Query(default="mikan", description="数据源"),
    current_user: User = Depends(get_current_active_user),
):
    source = get_data_source(data_source)
    results = await source.search_by_keyword(keyword)

    return [
        SearchResult(
            title=r.title,
            episode_number=r.episode_number,
            torrent_url=r.torrent_url,
            magnet_url=r.magnet_url,
            subtitle_group=r.subtitle_group,
            publish_time=r.publish_time,
            file_size=r.file_size,
        )
        for r in results
    ]


@router.post("/refresh", response_model=MessageResponse)
async def refresh_bangumi_list(
    data_source: str = Query(default="mikan", description="数据源"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    source = get_data_source(data_source)
    await source.fetch_and_save_bangumi(session)

    return MessageResponse(message="番剧列表刷新成功")


@router.get("/{bangumi_id}", response_model=BangumiResponse)
async def get_bangumi_detail(
    bangumi_id: int,
    data_source: str = Query(default="mikan", description="数据源"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(Bangumi).options(selectinload(Bangumi.episodes)).where(Bangumi.id == bangumi_id)
    )
    bangumi = result.scalar_one_or_none()

    if not bangumi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="番剧不存在")

    if not bangumi.episodes:
        source = get_data_source(data_source)
        episode_infos = await source.fetch_episode_of_bangumi(bangumi.keyword, max_page=1)
        
        for info in episode_infos:
            episode = Episode(
                bangumi_id=bangumi.id,
                title=info.title,
                episode_number=info.episode_number,
                torrent_url=info.torrent_url,
                magnet_url=info.magnet_url,
                file_size=info.file_size,
                subtitle_group=info.subtitle_group,
                publish_time=info.publish_time,
            )
            session.add(episode)
        
        await session.commit()
        await session.refresh(bangumi, ["episodes"])

    return bangumi


@router.post("/{bangumi_id}/refresh-episodes", response_model=MessageResponse)
async def refresh_bangumi_episodes(
    bangumi_id: int,
    data_source: str = Query(default="mikan", description="数据源"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(Bangumi).options(selectinload(Bangumi.episodes)).where(Bangumi.id == bangumi_id)
    )
    bangumi = result.scalar_one_or_none()

    if not bangumi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="番剧不存在")

    source = get_data_source(data_source)
    episode_infos = await source.fetch_episode_of_bangumi(bangumi.keyword, max_page=3)

    existing_episodes = {ep.title: ep for ep in bangumi.episodes}
    updated_count = 0
    added_count = 0

    for info in episode_infos:
        if info.title in existing_episodes:
            ep = existing_episodes[info.title]
            if not ep.torrent_url and info.torrent_url:
                ep.torrent_url = info.torrent_url
                updated_count += 1
            if not ep.magnet_url and info.magnet_url:
                ep.magnet_url = info.magnet_url
        else:
            episode = Episode(
                bangumi_id=bangumi.id,
                title=info.title,
                episode_number=info.episode_number,
                torrent_url=info.torrent_url,
                magnet_url=info.magnet_url,
                file_size=info.file_size,
                subtitle_group=info.subtitle_group,
                publish_time=info.publish_time,
            )
            session.add(episode)
            added_count += 1

    await session.commit()

    return MessageResponse(message=f"剧集刷新成功，新增 {added_count} 集，更新 {updated_count} 集")


@router.get("/{bangumi_id}/episodes", response_model=List[SearchResult])
async def get_bangumi_episodes(
    bangumi_id: int,
    max_page: int = Query(default=3, description="最大抓取页数"),
    data_source: str = Query(default="mikan", description="数据源"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(select(Bangumi).where(Bangumi.id == bangumi_id))
    bangumi = result.scalar_one_or_none()

    if not bangumi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="番剧不存在")

    source = get_data_source(data_source)
    episodes = await source.fetch_episode_of_bangumi(bangumi.keyword, max_page=max_page)

    return [
        SearchResult(
            title=ep.title,
            episode_number=ep.episode_number,
            torrent_url=ep.torrent_url,
            magnet_url=ep.magnet_url,
            subtitle_group=ep.subtitle_group,
            publish_time=ep.publish_time,
            file_size=ep.file_size,
        )
        for ep in episodes
    ]
