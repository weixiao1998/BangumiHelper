from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_active_user
from app.core.database import get_async_session
from app.models.models import Bangumi, Subscription, User
from app.schemas import (
    BangumiFilterCreate,
    BangumiFilterResponse,
    BangumiFilterUpdate,
    MessageResponse,
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
)

router = APIRouter()


@router.get("", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.bangumi).selectinload(Bangumi.episodes))
        .where(Subscription.user_id == current_user.id)
    )
    subscriptions = result.scalars().all()

    return subscriptions


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_create: SubscriptionCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(select(Bangumi).where(Bangumi.id == subscription_create.bangumi_id))
    bangumi = result.scalar_one_or_none()

    if not bangumi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="番剧不存在")

    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id, Subscription.bangumi_id == subscription_create.bangumi_id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已经订阅了该番剧")

    subscription = Subscription(
        user_id=current_user.id,
        bangumi_id=subscription_create.bangumi_id,
        auto_download=subscription_create.auto_download,
        downloader_id=subscription_create.downloader_id,
        save_path=subscription_create.save_path,
    )

    session.add(subscription)
    await session.commit()

    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.bangumi).selectinload(Bangumi.episodes))
        .where(Subscription.id == subscription.id)
    )
    subscription = result.scalar_one()

    return subscription


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    subscription_update: SubscriptionUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.bangumi))
        .where(Subscription.id == subscription_id, Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅不存在")

    update_data = subscription_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subscription, field, value)

    await session.commit()
    await session.refresh(subscription)

    return subscription


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


@router.post("/{subscription_id}/mark", response_model=MessageResponse)
async def mark_episode(
    subscription_id: int,
    episode: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(Subscription).where(Subscription.id == subscription_id, Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅不存在")

    subscription.current_episode = episode
    await session.commit()

    return MessageResponse(message=f"已标记为第 {episode} 集")


@router.post("/{subscription_id}/filter", response_model=BangumiFilterResponse, status_code=status.HTTP_201_CREATED)
async def create_filter(
    subscription_id: int,
    filter_create: BangumiFilterCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.bangumi))
        .where(Subscription.id == subscription_id, Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅不存在")

    from app.models.models import BangumiFilter

    filter_obj = BangumiFilter(
        user_id=current_user.id,
        bangumi_name=subscription.bangumi.name,
        include_keywords=filter_create.include_keywords,
        exclude_keywords=filter_create.exclude_keywords,
        subtitle_groups=filter_create.subtitle_groups,
        regex_pattern=filter_create.regex_pattern,
        min_episode=filter_create.min_episode,
        max_episode=filter_create.max_episode,
    )

    session.add(filter_obj)
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
    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.bangumi))
        .where(Subscription.id == subscription_id, Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅不存在")

    from app.models.models import BangumiFilter

    result = await session.execute(
        select(BangumiFilter).where(
            BangumiFilter.user_id == current_user.id, BangumiFilter.bangumi_name == subscription.bangumi.name
        )
    )
    filter_obj = result.scalar_one_or_none()

    if not filter_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="过滤器不存在")

    update_data = filter_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(filter_obj, field, value)

    await session.commit()
    await session.refresh(filter_obj)

    return filter_obj
