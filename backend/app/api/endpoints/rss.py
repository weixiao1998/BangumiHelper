import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_active_user
from app.core.database import get_async_session
from app.core.filter_utils import filter_episodes, select_filter
from app.models.models import Episode, GlobalFilter, Subscription, User
from app.services.rss_feed import apply_window, build_feed, resolve_window

router = APIRouter()
# 兼容旧链接：单订阅 feed 原本挂在 /downloaders/rss/{id} 下（该功能已移除，仅保留此转发路由）
legacy_router = APIRouter()


async def _get_global_filter(session: AsyncSession, user_id: int) -> GlobalFilter | None:
    result = await session.execute(select(GlobalFilter).where(GlobalFilter.user_id == user_id))
    return result.scalar_one_or_none()


def _feed_response(content: str) -> Response:
    return Response(content=content, media_type="application/xml")


def _base_url(request: Request) -> str:
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    return f"{scheme}://{host}"


async def _subscription_feed(
    subscription_id: int,
    token: str,
    request: Request,
    session: AsyncSession,
    days: int | None,
    limit: int | None,
) -> Response:
    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.bangumi), selectinload(Subscription.filter))
        .where(Subscription.id == subscription_id, Subscription.rss_token == token)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅不存在或token无效")

    # 暂停的订阅明确失败，避免客户端把"空 feed"当成"没有更新"而静默失效
    if subscription.status != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该订阅已暂停")

    window_days, window_limit = resolve_window(days, limit)
    stmt = apply_window(
        select(Episode).where(Episode.bangumi_id == subscription.bangumi_id), window_days
    )
    episodes = (await session.execute(stmt)).scalars().all()

    global_filter = await _get_global_filter(session, subscription.user_id)
    # filter_mode 决定用全局默认规则还是订阅自身规则（互斥，不叠加）
    active_filter = select_filter(subscription.filter, global_filter, subscription.filter_mode)
    episodes = filter_episodes(list(episodes), active_filter)
    # 条数上限在过滤之后生效，保证"窗口内有命中却返回空"不会发生
    if window_limit is not None:
        episodes = episodes[:window_limit]

    content = build_feed(
        title=f"[BangumiHelper] {subscription.bangumi.name}",
        link=f"{_base_url(request)}/bangumi/{subscription.bangumi.id}",
        description=f"{subscription.bangumi.name} 的订阅 RSS",
        entries=[(None, ep) for ep in episodes],
    )
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

    # 只取启用的订阅：暂停的订阅不出现在聚合 feed 中
    subs_result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.bangumi), selectinload(Subscription.filter))
        .where(Subscription.user_id == user.id, Subscription.status == 1)
    )
    subscriptions = subs_result.scalars().all()
    subscription_by_bangumi = {sub.bangumi_id: sub for sub in subscriptions}

    base_url = _base_url(request)
    feed_title = f"[BangumiHelper] {user.username} 的订阅"

    if not subscriptions:
        return _feed_response(
            build_feed(
                title=feed_title,
                link=f"{base_url}/subscriptions",
                description=f"{user.username} 的聚合订阅 RSS",
                entries=[],
            )
        )

    window_days, window_limit = resolve_window(days, limit)
    stmt = apply_window(
        select(Episode).where(Episode.bangumi_id.in_(list(subscription_by_bangumi.keys()))), window_days
    )
    episodes = (await session.execute(stmt)).scalars().all()

    global_filter = await _get_global_filter(session, user.id)
    # 每个订阅按各自的 filter_mode 解析出生效规则，避免每个 episode 重复计算
    active_by_bangumi = {
        sub.bangumi_id: select_filter(sub.filter, global_filter, sub.filter_mode)
        for sub in subscriptions
    }
    entries: list[tuple[str | None, Episode]] = []
    for ep in episodes:
        sub = subscription_by_bangumi.get(ep.bangumi_id)
        if sub is None:  # 理论上不会发生，防御性跳过
            continue
        if filter_episodes([ep], active_by_bangumi[ep.bangumi_id]):
            entries.append((sub.bangumi.name, ep))

    # 顺序来自 SQL 的 publish_time desc，过滤不改变顺序，这里再按条数截断
    if window_limit is not None:
        entries = entries[:window_limit]

    content = build_feed(
        title=feed_title,
        link=f"{base_url}/subscriptions",
        description=f"{user.username} 的聚合订阅 RSS",
        entries=entries,
    )
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
    """用户级聚合 feed：该用户全部「启用」订阅的更新，按发布时间倒序。"""
    return await _user_feed(user_id, token, request, session, days, limit)


@router.get("/subscription/{subscription_id}")
async def get_subscription_rss_feed(
    subscription_id: int,
    token: str,
    request: Request,
    days: int | None = Query(default=None, description="时间窗口天数，0 表示不限，默认 60"),
    limit: int | None = Query(default=None, description="最大条数，0 表示不限，默认 100"),
    session: AsyncSession = Depends(get_async_session),
):
    """单订阅 feed：只包含该番剧命中过滤条件的更新。"""
    return await _subscription_feed(subscription_id, token, request, session, days, limit)


@router.post("/subscription/{subscription_id}/regenerate")
async def regenerate_subscription_rss_token(
    subscription_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(Subscription).where(
            Subscription.id == subscription_id, Subscription.user_id == current_user.id
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅不存在")

    subscription.rss_token = secrets.token_hex(32)
    await session.commit()

    return {"rss_token": subscription.rss_token}


# ---- 旧路径兼容（原 /downloaders/rss/... 命名空间已随下载器功能移除） ----
# 已把链接加进下载器的用户不应因为这次重构而失效，保留一个版本的转发。


@legacy_router.get("/rss/{subscription_id}")
async def legacy_get_rss_feed(
    subscription_id: int,
    token: str,
    request: Request,
    days: int | None = Query(default=None, description="时间窗口天数，0 表示不限，默认 60"),
    limit: int | None = Query(default=None, description="最大条数，0 表示不限，默认 100"),
    session: AsyncSession = Depends(get_async_session),
):
    return await _subscription_feed(subscription_id, token, request, session, days, limit)


@legacy_router.post("/rss/{subscription_id}/regenerate")
async def legacy_regenerate_rss_token(
    subscription_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    return await regenerate_subscription_rss_token(subscription_id, session, current_user)
