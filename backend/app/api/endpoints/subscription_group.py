import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_active_user
from app.core.database import get_async_session
from app.models.models import Subscription, SubscriptionGroup, User
from app.schemas import (
    MessageResponse,
    SubscriptionGroupCreate,
    SubscriptionGroupResponse,
    SubscriptionGroupUpdate,
)

router = APIRouter()

FILTER_FIELDS = (
    "include_keywords",
    "exclude_keywords",
    "subtitle_groups",
    "language",
    "regex_pattern",
    "min_episode",
    "max_episode",
)


async def _get_user_group(group_id: int, user_id: int, session: AsyncSession) -> SubscriptionGroup:
    result = await session.execute(
        select(SubscriptionGroup).where(
            SubscriptionGroup.id == group_id,
            SubscriptionGroup.user_id == user_id,
        )
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订阅组不存在")
    return group


async def _ensure_unique_name(
    name: str,
    user_id: int,
    session: AsyncSession,
    exclude_id: int | None = None,
) -> None:
    stmt = select(SubscriptionGroup.id).where(
        SubscriptionGroup.user_id == user_id,
        func.lower(SubscriptionGroup.name) == name.lower(),
    )
    if exclude_id is not None:
        stmt = stmt.where(SubscriptionGroup.id != exclude_id)
    if (await session.execute(stmt)).scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="订阅组名称已存在")


def _normalized_name(name: str | None) -> str:
    normalized = (name or "").strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="订阅组名称不能为空")
    if len(normalized) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="订阅组名称不能超过 50 个字符")
    return normalized


@router.get("", response_model=list[SubscriptionGroupResponse])
async def get_subscription_groups(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(SubscriptionGroup)
        .where(SubscriptionGroup.user_id == current_user.id)
        .order_by(SubscriptionGroup.created_at, SubscriptionGroup.id)
    )
    return result.scalars().all()


@router.get("/{group_id}", response_model=SubscriptionGroupResponse)
async def get_subscription_group(
    group_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    return await _get_user_group(group_id, current_user.id, session)


@router.post("", response_model=SubscriptionGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription_group(
    group_create: SubscriptionGroupCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    name = _normalized_name(group_create.name)
    await _ensure_unique_name(name, current_user.id, session)

    group = SubscriptionGroup(
        user_id=current_user.id,
        name=name,
        description=group_create.description,
        rss_token=secrets.token_hex(32),
        **{field: getattr(group_create, field) for field in FILTER_FIELDS},
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return group


@router.put("/{group_id}", response_model=SubscriptionGroupResponse)
async def update_subscription_group(
    group_id: int,
    group_update: SubscriptionGroupUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    group = await _get_user_group(group_id, current_user.id, session)
    update_data = group_update.model_dump(exclude_unset=True)

    if "name" in update_data:
        name = _normalized_name(update_data["name"])
        await _ensure_unique_name(name, current_user.id, session, exclude_id=group.id)
        group.name = name

    if "description" in update_data:
        group.description = update_data["description"]

    if "status" in update_data:
        value = update_data["status"]
        if value not in (0, 1):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="订阅组状态只能是 0 或 1")
        group.status = value

    for field in FILTER_FIELDS:
        if field in update_data:
            setattr(group, field, update_data[field])

    await session.commit()
    await session.refresh(group)
    return group


@router.delete("/{group_id}", response_model=MessageResponse)
async def delete_subscription_group(
    group_id: int,
    delete_subscriptions: bool = Query(default=False, description="是否同时删除组内订阅"),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    group = await _get_user_group(group_id, current_user.id, session)

    group_count = await session.scalar(
        select(func.count()).select_from(SubscriptionGroup).where(SubscriptionGroup.user_id == current_user.id)
    )
    if (group_count or 0) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少保留一个订阅组")

    subscription_count = (
        await session.scalar(
            select(func.count()).select_from(Subscription).where(Subscription.group_id == group.id)
        )
    ) or 0

    if subscription_count and not delete_subscriptions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"订阅组内还有 {subscription_count} 个订阅，请确认是否一并取消",
        )

    if subscription_count:
        # 预加载订阅及其自定义规则，确保 ORM 级联删除生效
        result = await session.execute(
            select(SubscriptionGroup)
            .options(selectinload(SubscriptionGroup.subscriptions).selectinload(Subscription.filter))
            .where(SubscriptionGroup.id == group.id)
        )
        group = result.scalar_one()

    await session.delete(group)
    await session.commit()

    if subscription_count:
        return MessageResponse(message=f"订阅组已删除，同时取消 {subscription_count} 个订阅")
    return MessageResponse(message="订阅组已删除")
