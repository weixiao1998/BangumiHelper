
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_active_user
from app.core.constants import FilterMode
from app.core.database import get_async_session
from app.core.filter_utils import describe_source, filter_episodes, has_conditions, select_filter
from app.models.models import Bangumi, BangumiFilter, Episode, Subscription, SubscriptionGroup, User
from app.schemas import (
    BangumiFilterCreate,
    BangumiFilterResponse,
    BangumiFilterUpdate,
    MessageResponse,
    SubscriptionCreate,
    SubscriptionFilteringResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
)

router = APIRouter()

SUBSCRIPTION_BASE_OPTIONS = (
    selectinload(Subscription.bangumi).selectinload(Bangumi.episodes),
    # BangumiResponse.seasons 需要该关系；缺失会在响应序列化时触发懒加载 → MissingGreenlet → 500
    selectinload(Subscription.bangumi).selectinload(Bangumi.seasons),
    selectinload(Subscription.filter),
    # SubscriptionResponse.group 需要该关系；缺失会在序列化时触发懒加载 → MissingGreenlet
    selectinload(Subscription.group),
)


async def _get_user_subscription(subscription_id: int, user_id: int, session: AsyncSession) -> Subscription:
    result = await session.execute(
        select(Subscription)
        .options(*SUBSCRIPTION_BASE_OPTIONS)
        .where(Subscription.id == subscription_id, Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅不存在")
    return subscription


@router.get("", response_model=list[SubscriptionResponse])
async def get_subscriptions(
    group_id: int | None = Query(default=None, description="只看某个订阅组"),
    bangumi_id: int | None = Query(default=None, description="只看某部番剧在各组的订阅"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    stmt = (
        select(Subscription)
        .options(*SUBSCRIPTION_BASE_OPTIONS)
        .where(Subscription.user_id == current_user.id)
    )
    if group_id is not None:
        stmt = stmt.where(Subscription.group_id == group_id)
    if bangumi_id is not None:
        stmt = stmt.where(Subscription.bangumi_id == bangumi_id)

    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_create: SubscriptionCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    bangumi_result = await session.execute(select(Bangumi).where(Bangumi.id == subscription_create.bangumi_id))
    bangumi = bangumi_result.scalar_one_or_none()

    if not bangumi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="番剧不存在")

    group_result = await session.execute(
        select(SubscriptionGroup).where(
            SubscriptionGroup.id == subscription_create.group_id,
            SubscriptionGroup.user_id == current_user.id,
        )
    )
    if group_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅组不存在")

    dup_result = await session.execute(
        select(Subscription).where(
            Subscription.group_id == subscription_create.group_id,
            Subscription.bangumi_id == subscription_create.bangumi_id,
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该订阅组已经订阅了这部番剧")

    filter_fields = subscription_create.model_dump(exclude_unset=True)
    filter_field_names = {
        "include_keywords",
        "exclude_keywords",
        "subtitle_groups",
        "language",
        "regex_pattern",
        "min_episode",
        "max_episode",
    }
    filter_fields = {k: v for k, v in filter_fields.items() if k in filter_field_names and v is not None}

    # 未显式指定时按是否提供了过滤条件推断：有=自定义，无=继承组默认规则。
    # 自定义模式下允许不带任何条件：表示"这个订阅不做过滤"。
    mode = subscription_create.filter_mode or (FilterMode.CUSTOM if filter_fields else FilterMode.INHERIT)
    if mode == FilterMode.INHERIT and filter_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="继承订阅组默认规则时不应提交自定义过滤条件",
        )

    subscription = Subscription(
        user_id=current_user.id,
        group_id=subscription_create.group_id,
        bangumi_id=subscription_create.bangumi_id,
        filter_mode=mode,
    )

    session.add(subscription)
    await session.flush()

    if filter_fields:
        session.add(
            BangumiFilter(
                user_id=current_user.id,
                subscription_id=subscription.id,
                bangumi_name=bangumi.name,
                **filter_fields,
            )
        )

    await session.commit()

    created_result = await session.execute(
        select(Subscription)
        .options(*SUBSCRIPTION_BASE_OPTIONS)
        .where(Subscription.id == subscription.id)
    )
    return created_result.scalar_one()


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    subscription_update: SubscriptionUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    subscription = await _get_user_subscription(subscription_id, current_user.id, session)

    update_data = subscription_update.model_dump(exclude_unset=True)

    target_group_id = update_data.pop("group_id", None)
    if target_group_id is not None and target_group_id != subscription.group_id:
        target_group_result = await session.execute(
            select(SubscriptionGroup).where(
                SubscriptionGroup.id == target_group_id,
                SubscriptionGroup.user_id == current_user.id,
            )
        )
        if target_group_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅组不存在")

        dup_result = await session.execute(
            select(Subscription.id).where(
                Subscription.group_id == target_group_id,
                Subscription.bangumi_id == subscription.bangumi_id,
            )
        )
        if dup_result.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="目标订阅组已订阅该番剧")

        subscription.group_id = target_group_id

    for field, value in update_data.items():
        setattr(subscription, field, value)

    await session.commit()

    # 重新查询并带全关系，避免响应序列化访问 group 时触发懒加载。
    # populate_existing 必须有：移动订阅组后 session 里仍缓存着旧的 group 关系，
    # 不加会把旧组返回给前端，直到下次刷新页面才正确。
    updated_result = await session.execute(
        select(Subscription)
        .options(*SUBSCRIPTION_BASE_OPTIONS)
        .where(Subscription.id == subscription.id)
        .execution_options(populate_existing=True)
    )
    return updated_result.scalar_one()


@router.delete("/{subscription_id}", response_model=MessageResponse)
async def delete_subscription(
    subscription_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(Subscription).where(Subscription.id == subscription_id, Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅不存在")

    await session.delete(subscription)
    await session.commit()

    return MessageResponse(message="取消订阅成功")


@router.get("/{subscription_id}/filtering", response_model=SubscriptionFilteringResponse)
async def get_subscription_filtering(
    subscription_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """返回该订阅当前生效的过滤规则来源与命中的剧集 id。

    过滤判定只在后端实现一处，前端据此置灰/标记，避免两端逻辑漂移
    （历史上详情页复制过一份判定，必须避免两端漂移）。
    """
    subscription = await _get_user_subscription(subscription_id, current_user.id, session)

    active_filter = select_filter(subscription.filter, subscription.group, subscription.filter_mode)

    episodes_result = await session.execute(
        select(Episode).where(Episode.bangumi_id == subscription.bangumi_id)
    )
    episodes = list(episodes_result.scalars().all())
    matched = filter_episodes(episodes, active_filter)

    return SubscriptionFilteringResponse(
        filter_mode=subscription.filter_mode,
        active_source=describe_source(subscription.filter, subscription.group, subscription.filter_mode),
        group_filter_available=has_conditions(subscription.group),
        active_subtitle_groups=active_filter.subtitle_groups if active_filter else None,
        matched_episode_ids=[ep.id for ep in matched],
    )


@router.get("/{subscription_id}/filter", response_model=BangumiFilterResponse | None)
async def get_filter(
    subscription_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    subscription = await _get_user_subscription(subscription_id, current_user.id, session)
    return subscription.filter


@router.post("/{subscription_id}/filter", response_model=BangumiFilterResponse, status_code=status.HTTP_201_CREATED)
async def create_filter(
    subscription_id: int,
    filter_create: BangumiFilterCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    subscription = await _get_user_subscription(subscription_id, current_user.id, session)

    if subscription.filter:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="过滤器已存在，请使用更新接口")

    filter_obj = BangumiFilter(
        user_id=current_user.id,
        subscription_id=subscription.id,
        bangumi_name=subscription.bangumi.name,
        include_keywords=filter_create.include_keywords,
        exclude_keywords=filter_create.exclude_keywords,
        subtitle_groups=filter_create.subtitle_groups,
        language=filter_create.language,
        regex_pattern=filter_create.regex_pattern,
        min_episode=filter_create.min_episode,
        max_episode=filter_create.max_episode,
    )

    session.add(filter_obj)
    # 新建规则即视为用户想让它生效，直接切到自定义模式
    subscription.filter_mode = FilterMode.CUSTOM
    await session.commit()
    await session.refresh(filter_obj)

    return filter_obj


@router.put("/{subscription_id}/filter", response_model=BangumiFilterResponse)
async def update_filter(
    subscription_id: int,
    filter_update: BangumiFilterUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    subscription = await _get_user_subscription(subscription_id, current_user.id, session)

    if not subscription.filter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="过滤器不存在，请先创建")

    update_data = filter_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subscription.filter, field, value)

    await session.commit()
    await session.refresh(subscription.filter)

    return subscription.filter


@router.delete("/{subscription_id}/filter", response_model=MessageResponse)
async def delete_filter(
    subscription_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    subscription = await _get_user_subscription(subscription_id, current_user.id, session)

    if not subscription.filter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="过滤器不存在")

    await session.delete(subscription.filter)
    # 规则没了就无法再"自定义"，回落到继承订阅组默认规则
    subscription.filter_mode = FilterMode.INHERIT
    await session.commit()

    return MessageResponse(message="过滤器已删除")
