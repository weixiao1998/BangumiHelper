from datetime import UTC

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_active_user
from app.core.database import async_session_maker, get_async_session
from app.core.utils import utc_now
from app.models.models import Bangumi, BangumiSeason, Episode, Subscription, User
from app.schemas import BangumiListResponse, BangumiResponse, CalendarResponse, MessageResponse, SearchResult
from app.services.cover_cache import get_cover_response
from app.services.data_sources import get_data_source

router = APIRouter()

# 详情页剧集异步刷新的最小间隔（秒）：进入详情页时距上次剧集检查不足该时间则不重复拉取。
_DETAIL_EPISODE_REFRESH_INTERVAL = 10 * 60  # 10 分钟


async def _background_refresh_episodes(bangumi_id: int, data_source: str) -> None:
    """详情页触发的后台剧集刷新：拉取新剧集入库，不阻塞请求响应。"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Bangumi).options(selectinload(Bangumi.episodes)).where(Bangumi.id == bangumi_id)
            )
            bangumi = result.scalar_one_or_none()
            if not bangumi:
                return

            source = await get_data_source(data_source)
            try:
                episode_infos = await source.fetch_episode_of_bangumi(bangumi.keyword, max_page=2)
                existing = {ep.title: ep for ep in bangumi.episodes}
                for info in episode_infos:
                    if info.title in existing:
                        ep = existing[info.title]
                        if not ep.torrent_url and info.torrent_url:
                            ep.torrent_url = info.torrent_url
                        if not ep.magnet_url and info.magnet_url:
                            ep.magnet_url = info.magnet_url
                    else:
                        session.add(
                            Episode(
                                bangumi_id=bangumi.id,
                                title=info.title,
                                episode_number=info.episode_number,
                                torrent_url=info.torrent_url,
                                magnet_url=info.magnet_url,
                                file_size=info.file_size,
                                subtitle_group=info.subtitle_group,
                                publish_time=info.publish_time,
                            )
                        )
                bangumi.last_episode_check_at = utc_now()
                await session.commit()
            finally:
                await source.close()
    except Exception:
        logger.exception(f"[BangumiDetail] Background episode refresh failed for bangumi {bangumi_id}")


@router.get("/calendar", response_model=list[CalendarResponse])
async def get_calendar(
    data_source: str = Query(default="mikan", description="数据源"),
    year: int | None = Query(default=None, description="年份，如 2025；与 season 一起指定则只返回该季度番剧"),
    season: str | None = Query(default=None, description="季度：春/夏/秋/冬"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    if year is not None and season is not None:
        stmt = (
            select(Bangumi)
            .join(BangumiSeason, BangumiSeason.bangumi_id == Bangumi.id)
            .where(
                Bangumi.data_source == data_source,
                BangumiSeason.year == year,
                BangumiSeason.season == season,
            )
            .options(selectinload(Bangumi.seasons))
        )
    else:
        stmt = select(Bangumi).where(Bangumi.data_source == data_source).options(selectinload(Bangumi.seasons))
    result = await session.execute(stmt)
    db_bangumi_list = result.scalars().all()

    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.bangumi))
        .where(Subscription.user_id == current_user.id)
    )
    subscriptions = {sub.bangumi.name: sub for sub in result.scalars().all()}

    weekday_map: dict[str, list[BangumiListResponse]] = {}
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
            seasons=[f"{s.year} {s.season}" for s in bangumi.seasons],
        )

        weekday = bangumi.update_time.lower()
        if weekday not in weekday_map:
            weekday_map[weekday] = []
        weekday_map[weekday].append(bangumi_response)

    calendar = [CalendarResponse(weekday=day, bangumi_list=bangumis) for day, bangumis in weekday_map.items()]

    return calendar


@router.get("/search", response_model=list[SearchResult])
async def search_bangumi(
    keyword: str = Query(..., description="搜索关键词"),
    data_source: str = Query(default="mikan", description="数据源"),
    current_user: User = Depends(get_current_active_user),
):
    source = await get_data_source(data_source)
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
    year: int | None = Query(default=None, description="年份，如 2025；与 season 一起指定则按该季度刷新"),
    season: str | None = Query(default=None, description="季度：春/夏/秋/冬"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    source = await get_data_source(data_source)
    await source.fetch_and_save_bangumi(session, year=year, season=season)

    return MessageResponse(message="番剧列表刷新成功")


@router.get("/{bangumi_id}", response_model=BangumiResponse)
async def get_bangumi_detail(
    bangumi_id: int,
    background_tasks: BackgroundTasks,
    data_source: str = Query(default="mikan", description="数据源"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(Bangumi)
        .options(selectinload(Bangumi.episodes), selectinload(Bangumi.seasons))
        .where(Bangumi.id == bangumi_id)
    )
    bangumi = result.scalar_one_or_none()

    if not bangumi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="番剧不存在")

    source = await get_data_source(data_source)

    # 判断是否需要拉取新剧集：距上次剧集检查 ≥ 10 分钟才拉，避免每次都拉
    last_check = bangumi.last_episode_check_at
    if last_check is not None and last_check.tzinfo is None:
        last_check = last_check.replace(tzinfo=UTC)
    needs_refresh = last_check is None or (utc_now() - last_check).total_seconds() >= _DETAIL_EPISODE_REFRESH_INTERVAL

    if not bangumi.episodes:
        # 首次（无剧集记录）：同步拉一次，保证详情页有数据；并记录检查时间
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

        bangumi.last_episode_check_at = utc_now()
        await session.commit()
        await session.refresh(bangumi, ["episodes"])
    elif needs_refresh:
        # 已有剧集且距上次检查 ≥ 10 分钟：后台异步刷新，不阻塞响应
        background_tasks.add_task(_background_refresh_episodes, bangumi.id, data_source)

    if not bangumi.subtitle_groups:
        bangumi_info = await source.fetch_single_bangumi(bangumi.keyword)
        if bangumi_info and bangumi_info.subtitle_groups:
            bangumi.subtitle_groups = bangumi_info.subtitle_groups
            await session.commit()
            await session.refresh(bangumi)

    return bangumi


@router.get("/{bangumi_id}/cover")
async def get_bangumi_cover(
    bangumi_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    # 封面代理：首次从外部源下载并缓存到本地，之后由后端直接提供，
    # 避免图片重复加载。该接口免认证，因为 <img> 标签无法携带 JWT header。
    result = await session.execute(select(Bangumi).where(Bangumi.id == bangumi_id))
    bangumi = result.scalar_one_or_none()

    if not bangumi or not bangumi.cover:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="封面不存在")

    return await get_cover_response(bangumi.cover)


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

    source = await get_data_source(data_source)
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

    if not bangumi.subtitle_groups:
        bangumi_info = await source.fetch_single_bangumi(bangumi.keyword)
        if bangumi_info and bangumi_info.subtitle_groups:
            bangumi.subtitle_groups = bangumi_info.subtitle_groups

    await session.commit()

    return MessageResponse(message=f"剧集刷新成功，新增 {added_count} 集，更新 {updated_count} 集")


@router.get("/{bangumi_id}/episodes", response_model=list[SearchResult])
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

    source = await get_data_source(data_source)
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
