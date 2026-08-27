import asyncio
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.utils import current_anime_season, utc_now
from app.models.models import Bangumi, Episode
from app.services.data_sources import get_available_data_sources, get_data_source

scheduler: AsyncIOScheduler | None = None

# 定时刷新剧集时的节流参数：串行抓取、番剧间限速，避免触发数据源限流。
# max_page 对 mikan 无效（仅解析单番剧详情页），取与手动刷新一致的默认值。
_EPISODE_REFRESH_MAX_PAGE = 3
_EPISODE_REFRESH_SLEEP_SECONDS = 2.0

# 每个番剧的剧集刷新采用「自适应退避」：
#   本次刷到新增 → 缩短 CD（更快），下限 1 小时；
#   本次无新增     → 拉长 CD（更省），上限 12 小时。
# 因为有上限，周更番剧在两次更新之间也至少每 12 小时刷一次，下一集更新时不会被漏掉。
_EPISODE_MIN_INTERVAL = 60 * 60          # 1h (秒)
_EPISODE_MAX_INTERVAL = 12 * 60 * 60     # 12h (秒)

# 滑动窗口：每轮最多刷新多少「到期」番剧。番剧总量增长时单轮请求量固定，不会无限上升。
_EPISODE_REFRESH_BATCH_SIZE = 20
# 最近一集发表时间距今超过该天数即视为停更，不再自动刷新（其后需手动刷新或该番剧恢复更新）。
_EPISODE_STALE_DAYS = 15


async def refresh_bangumi_calendar():
    logger.info(f"[Scheduler] Starting bangumi calendar refresh at {datetime.now()}")

    # 当前正在播放的季度：自动刷新当前季并为番剧打上季度标签；历史季度由管理界面上手动刷新。
    year, season = current_anime_season()

    for source_name in get_available_data_sources():
        try:
            source = await get_data_source(source_name)
            async with async_session_maker() as session:
                bangumi_list = await source.fetch_and_save_bangumi(session, year=year, season=season)
                logger.info(f"[Scheduler] Refreshed {len(bangumi_list)} bangumi from {source_name}")

            await source.close()
        except Exception as e:
            logger.error(f"[Scheduler] Failed to refresh {source_name}: {e}")

    logger.info(f"[Scheduler] Bangumi calendar refresh completed at {datetime.now()}")


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


async def refresh_episodes(max_bangumi: int | None = None):
    """定时刷新番剧剧集：自适应 CD + 停更判定 + 每轮限量滑动刷新。

    - 每个番剧记录 last_episode_check_at / episode_check_interval（自适应 CD）；
    - 距上次检查超过自身 CD 才计入候选；但每轮最多只取
      _EPISODE_REFRESH_BATCH_SIZE 个「最久未刷」的到期番剧（滑动窗口），
      番剧总量增长时单轮请求量固定，不会无限上升；
    - 最近一集发表时间距今超过 _EPISODE_STALE_DAYS 天视为停更，不再自动刷新。
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

            # 1) 筛选到期（距上次检查 >= 自身 CD）且未停更的番剧
            due: list[tuple[datetime, Bangumi]] = []
            for bangumi in bangumi_list:
                interval = bangumi.episode_check_interval or _EPISODE_MIN_INTERVAL
                last_check = _as_utc(bangumi.last_episode_check_at)
                if last_check is not None and (now - last_check).total_seconds() < interval:
                    continue

                # 停更判定：最近一集发表时间距今超过 15 天（且已检查过）
                recent_publish = _as_utc(
                    max((ep.publish_time for ep in bangumi.episodes if ep.publish_time), default=None)
                )
                if (
                    last_check is not None
                    and recent_publish is not None
                    and (now - recent_publish).days > _EPISODE_STALE_DAYS
                ):
                    continue

                checked += 1
                # 从未检查过的排最前（优先建立基线）
                due.append((last_check if last_check is not None else datetime(1970, 1, 1, tzinfo=UTC), bangumi))

            # 2) 滑动窗口：按上次检查时间升序（越久未刷越优先）只取前 BATCH 个
            due.sort(key=lambda x: x[0])
            batch = due[:_EPISODE_REFRESH_BATCH_SIZE]

            for _, bangumi in batch:
                # 已移除的数据源（历史遗留行）不再自动刷新，直接跳过，避免每次报错
                if bangumi.data_source not in get_available_data_sources():
                    continue
                interval = bangumi.episode_check_interval or _EPISODE_MIN_INTERVAL
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
