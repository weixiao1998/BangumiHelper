import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.core.config import settings
from app.core.database import async_session_maker
from app.services.data_sources import get_data_source, get_available_data_sources

scheduler: AsyncIOScheduler | None = None


async def refresh_bangumi_calendar():
    logger.info(f"[Scheduler] Starting bangumi calendar refresh at {datetime.now()}")

    for source_name in get_available_data_sources():
        try:
            source = get_data_source(source_name)
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

    scheduler.start()
    logger.info(f"[Scheduler] Started with interval {settings.CALENDAR_REFRESH_INTERVAL} hours")

    await refresh_bangumi_calendar()


async def stop_scheduler():
    global scheduler

    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("[Scheduler] Stopped")
