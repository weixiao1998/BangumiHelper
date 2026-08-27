import asyncio
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.utils import utc_now
from app.models.models import Bangumi, Episode
from app.services.data_sources import get_available_data_sources, get_data_source

scheduler: AsyncIOScheduler | None = None

# 定时刷新剧集时的节流参数：串行抓取、番剧间限速，避免触发数据源限流。
# 注意 max_page 对 mikan 无效（仅解析单番剧详情页），对 dmhy 则是翻页数，取与手动刷新一致的 3 页以防漏集。
_EPISODE_REFRESH_MAX_PAGE = 3
_EPISODE_REFRESH_SLEEP_SECONDS = 2.0

# 每个番剧的剧集刷新采用「自适应退避」：
#   本次刷到新增 → 缩短 CD（更快），下限 1 小时；
#   本次无新增     → 拉长 CD（更省），上限 12 小时。
# 因为有上限，周更番剧在两次更新之间也至少每 12 小时刷一次，下一集更新时不会被漏掉。
_EPISODE_MIN_INTERVAL = 60 * 60          # 1h (秒)
_EPISODE_MAX_INTERVAL = 12 * 60 * 60     # 12h (秒)


async def refresh_bangumi_calendar():
    logger.info(f"[Scheduler] Starting bangumi calendar refresh at {datetime.now()}")

    for source_name in get_available_data_sources():
        try:
            source = await get_data_source(source_name)
            async with async_session_maker() as session:
                bangumi_list = await source.fetch_bangumi_calendar()

                from sqlalchemy import select

                from app.models.models import Bangumi

                for info in bangumi_list:
                    existing = await session.execute(
                        select(Bangumi).where(Bangumi.keyword == info.keyword)
                    )
                    if not existing.scalar_one_or_none():
                        bangumi = Bangumi(
                            name=info.name,
                            keyword=info.keyword,
                            cover=info.cover,
                            update_time=info.update_time,
                            status=info.status,
                            data_source=info.data_source,
                            subtitle_groups=info.subtitle_groups,
                            description=info.description,
                        )
                        session.add(bangumi)

                await session.commit()
                logger.info(f"[Scheduler] Refreshed {len(bangumi_list)} bangumi from {source_name}")

            await source.close()
        except Exception as e:
            logger.error(f"[Scheduler] Failed to refresh {source_name}: {e}")

    logger.info(f"[Scheduler] Bangumi calendar refresh completed at {datetime.now()}")


async def refresh_episodes(max_bangumi: int | None = None):
    """定时刷新番剧剧集：按每个番剧自身的自适应 CD 决定本轮是否刷新。

    每个番剧记录 last_episode_check_at / episode_check_interval；
    只在距上次检查超过自身 CD 时才抓取，其余番剧本轮跳过，避免每次全量刷新。
    仅入库，不触发下载。
    """
    logger.info(f"[Scheduler] Starting episode refresh at {datetime.now()}")

    sources: dict[str, object] = {}
    now = utc_now()
    checked = 0
    refreshed = 0
    added_total = 0
    try:
        async with async_session_maker() as session:
            result = await session.execute(select(Bangumi).options(selectinload(Bangumi.episodes)))
            bangumi_list = result.scalars().all()
            if max_bangumi is not None:
                bangumi_list = bangumi_list[:max_bangumi]

            for bangumi in bangumi_list:
                # 未到自身 CD 的番剧跳过，不请求数据源
                interval = bangumi.episode_check_interval or _EPISODE_MIN_INTERVAL
                last_check = bangumi.last_episode_check_at
                if last_check is not None:
                    if last_check.tzinfo is None:
                        last_check = last_check.replace(tzinfo=UTC)
                    if (now - last_check).total_seconds() < interval:
                        continue

                checked += 1
                try:
                    if bangumi.data_source not in sources:
                        sources[bangumi.data_source] = await get_data_source(bangumi.data_source)
                    source = sources[bangumi.data_source]

                    episode_infos = await source.fetch_episode_of_bangumi(
                        bangumi.keyword, max_page=_EPISODE_REFRESH_MAX_PAGE
                    )
                    existing = {ep.title: ep for ep in bangumi.episodes}
                    added = 0
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
                            added += 1

                    # 自适应退避：有新增则缩短 CD，无新增则拉长 CD（受上下限约束）
                    if added > 0:
                        new_interval = max(_EPISODE_MIN_INTERVAL, interval // 2)
                    else:
                        new_interval = min(_EPISODE_MAX_INTERVAL, interval * 2)
                    bangumi.last_episode_check_at = now
                    bangumi.episode_check_interval = new_interval

                    await session.commit()
                    refreshed += 1
                    added_total += added
                    await asyncio.sleep(_EPISODE_REFRESH_SLEEP_SECONDS)
                except Exception as e:
                    logger.error(f"[Scheduler] Failed to refresh episodes for {bangumi.name}: {e}")
                    await session.rollback()
    finally:
        for source in sources.values():
            await source.close()

    logger.info(
        f"[Scheduler] Episode refresh completed, checked {checked} bangumi, refreshed {refreshed}, "
        f"added {added_total} episodes"
    )


async def start_scheduler():
    global scheduler

    if scheduler is not None:
        logger.warning("[Scheduler] Scheduler already running")
        return

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        refresh_bangumi_calendar,
        trigger=IntervalTrigger(hours=settings.CALENDAR_REFRESH_INTERVAL),
        id="refresh_bangumi_calendar",
        replace_existing=True,
    )

    scheduler.add_job(
        refresh_episodes,
        trigger=IntervalTrigger(hours=settings.EPISODE_REFRESH_INTERVAL),
        id="refresh_episodes",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"[Scheduler] Started, calendar every {settings.CALENDAR_REFRESH_INTERVAL}h, episodes every "
        f"{settings.EPISODE_REFRESH_INTERVAL}h"
    )

    await refresh_bangumi_calendar()


async def stop_scheduler():
    global scheduler

    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("[Scheduler] Stopped")
