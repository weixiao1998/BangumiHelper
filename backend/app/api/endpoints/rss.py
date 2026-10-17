import secrets
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_active_user
from app.core.database import get_async_session
from app.core.filter_utils import select_filter
from app.models.models import Episode, Subscription, SubscriptionGroup, User
from app.services.rss_feed import apply_window, build_feed, collect_feed_entries, resolve_window

router = APIRouter()


def _feed_response(content: str) -> Response:
    return Response(content=content, media_type="application/xml")


def _base_url(request: Request) -> str:
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    return f"{scheme}://{host}"


async def _group_feed(
    group_id: int,
    token: str,
    request: Request,
    session: AsyncSession,
    days: int | None,
    limit: int | None,
) -> Response:
    group_result = await session.execute(
        select(SubscriptionGroup).where(
            SubscriptionGroup.id == group_id,
            SubscriptionGroup.rss_token == token,
        )
    )
    group = group_result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅组不存在或token无效")

    # 暂停的组明确失败，避免客户端把"空 feed"当成"没有更新"而静默失效
    if group.status != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该订阅组已暂停")

    base_url = _base_url(request)
    feed_title = f"[BangumiHelper] {group.name}"
    feed_link = f"{base_url}/subscriptions?group={group.id}"
    feed_description = f"{group.name} 的订阅组 RSS"

    subs_result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.bangumi), selectinload(Subscription.filter))
        .where(Subscription.group_id == group.id, Subscription.status == 1)
    )
    subscriptions = list(subs_result.scalars().all())

    if not subscriptions:
        return _feed_response(
            build_feed(title=feed_title, link=feed_link, description=feed_description, entries=[])
        )

    subscriptions_by_bangumi: dict[int, list[Subscription]] = defaultdict(list)
    for sub in subscriptions:
        subscriptions_by_bangumi[sub.bangumi_id].append(sub)

    # 组内每条订阅按自己的 filter_mode 解析：inherit=组规则，custom=自身规则
    active_filters = {
        sub.id: select_filter(sub.filter, group, sub.filter_mode) for sub in subscriptions
    }

    window_days, window_limit = resolve_window(days, limit)
    stmt = apply_window(
        select(Episode).where(Episode.bangumi_id.in_(list(subscriptions_by_bangumi.keys()))),
        window_days,
    )
    episodes = (await session.execute(stmt)).scalars().all()
    entries = collect_feed_entries(list(episodes), subscriptions_by_bangumi, active_filters)

    # 条数上限在过滤/去重之后生效，保证"窗口内有命中却返回空"不会发生
    if window_limit is not None:
        entries = entries[:window_limit]

    content = build_feed(title=feed_title, link=feed_link, description=feed_description, entries=entries)
    return _feed_response(content)


async def _user_feed(
    user_id: int,
    token: str,
    request: Request,
    session: AsyncSession,
    days: int | None,
    limit: int | None,
) -> Response:
    user_result = await session.execute(select(User).where(User.id == user_id, User.rss_token == token))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在或token无效")

    base_url = _base_url(request)
    feed_title = f"[BangumiHelper] {user.username} 的订阅"
    feed_link = f"{base_url}/subscriptions"
    feed_description = f"{user.username} 的聚合订阅 RSS"

    # 暂停组与暂停订阅都不进入聚合 feed
    subs_result = await session.execute(
        select(Subscription)
        .options(
            selectinload(Subscription.bangumi),
            selectinload(Subscription.filter),
            selectinload(Subscription.group),
        )
        .where(Subscription.user_id == user.id, Subscription.status == 1)
    )
    subscriptions = [sub for sub in subs_result.scalars().all() if sub.group.status == 1]

    if not subscriptions:
        return _feed_response(
            build_feed(title=feed_title, link=feed_link, description=feed_description, entries=[])
        )

    subscriptions_by_bangumi: dict[int, list[Subscription]] = defaultdict(list)
    for sub in subscriptions:
        subscriptions_by_bangumi[sub.bangumi_id].append(sub)

    # 同一番剧可能在多个组：各自解析生效规则，由 collect_feed_entries 按 episode 去重
    active_filters = {
        sub.id: select_filter(sub.filter, sub.group, sub.filter_mode) for sub in subscriptions
    }

    window_days, window_limit = resolve_window(days, limit)
    stmt = apply_window(
        select(Episode).where(Episode.bangumi_id.in_(list(subscriptions_by_bangumi.keys()))),
        window_days,
    )
    episodes = (await session.execute(stmt)).scalars().all()
    entries = collect_feed_entries(list(episodes), subscriptions_by_bangumi, active_filters)

    if window_limit is not None:
        entries = entries[:window_limit]

    content = build_feed(title=feed_title, link=feed_link, description=feed_description, entries=entries)
    return _feed_response(content)


@router.get("/user/{user_id}")
async def get_user_rss_feed(
    user_id: int,
    token: str,
    request: Request,
    days: int | None = Query(default=None, description="时间窗口天数，0 表示不限，默认 60"),
    limit: int | None = Query(default=None, description="最大条数，0 表示不限，默认 100"),
    session: AsyncSession = Depends(get_async_session),
):
    """用户级聚合 feed：该用户全部「启用」组中「启用」订阅的更新，按发布时间倒序并去重。"""
    return await _user_feed(user_id, token, request, session, days, limit)


@router.get("/group/{group_id}")
async def get_group_rss_feed(
    group_id: int,
    token: str,
    request: Request,
    days: int | None = Query(default=None, description="时间窗口天数，0 表示不限，默认 60"),
    limit: int | None = Query(default=None, description="最大条数，0 表示不限，默认 100"),
    session: AsyncSession = Depends(get_async_session),
):
    """组 feed：只包含该订阅组内启用订阅的更新，按各订阅的生效规则过滤。"""
    return await _group_feed(group_id, token, request, session, days, limit)


@router.post("/group/{group_id}/regenerate")
async def regenerate_group_rss_token(
    group_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(SubscriptionGroup).where(
            SubscriptionGroup.id == group_id,
            SubscriptionGroup.user_id == current_user.id,
        )
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅组不存在")

    group.rss_token = secrets.token_hex(32)
    await session.commit()

    return {"rss_token": group.rss_token}
