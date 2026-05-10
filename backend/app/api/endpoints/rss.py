from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Response, status
from feedgenerator import Rss201rev2Feed
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.core.filter_utils import filter_episodes
from app.models.models import Bangumi, GlobalFilter, Subscription, User

router = APIRouter()


@router.get("/user/{user_id}")
async def get_user_rss_feed(
    user_id: int,
    token: str,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(User).where(User.id == user_id, User.rss_token == token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在或token无效")

    result = await session.execute(
        select(Subscription)
        .options(
            selectinload(Subscription.bangumi).selectinload(Bangumi.episodes),
            selectinload(Subscription.filter),
        )
        .where(Subscription.user_id == user.id)
    )
    subscriptions = result.scalars().all()

    result = await session.execute(
        select(GlobalFilter).where(GlobalFilter.user_id == user.id)
    )
    global_filter = result.scalar_one_or_none()

    feed = Rss201rev2Feed(
        title=f"{user.username} - BangumiHelper",
        link="https://example.com",
        description="用户聚合RSS订阅",
    )

    for sub in subscriptions:
        episodes = filter_episodes(sub.bangumi.episodes, sub.filter, global_filter)

        for ep in episodes:
            description_parts = [f"[{sub.bangumi.name}] 第 {ep.episode_number} 集"]
            if ep.file_size:
                size_mb = ep.file_size / (1024 * 1024)
                description_parts.append(f"[{size_mb:.2f} MB]")
            if ep.subtitle_group:
                description_parts.append(f"字幕组: {ep.subtitle_group}")

            link = ep.magnet_url or ep.torrent_url or ""

            pubdate = None
            if ep.publish_time:
                if ep.publish_time.tzinfo is None:
                    pubdate = ep.publish_time.replace(tzinfo=UTC)
                else:
                    pubdate = ep.publish_time

            enclosure = None
            if ep.torrent_url:
                enclosure = {
                    "url": ep.torrent_url,
                    "length": int(ep.file_size) if ep.file_size else 0,
                    "mime_type": "application/x-bittorrent",
                }

            feed.add_item(
                title=f"[{sub.bangumi.name}] {ep.title}",
                link=link,
                description=" ".join(description_parts),
                unique_id=f"episode-{ep.id}",
                pubdate=pubdate,
                enclosure=enclosure,
            )

    rss_content = feed.writeString("utf-8")

    return Response(content=rss_content, media_type="application/xml")
