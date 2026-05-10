from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_active_user
from app.core.database import get_async_session
from app.models.models import GlobalFilter, User
from app.schemas import (
    GlobalFilterCreate,
    GlobalFilterResponse,
    GlobalFilterUpdate,
    MessageResponse,
    UserResponse,
)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.put("/me/password", response_model=MessageResponse)
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    from app.core.security import get_password_hash, verify_password

    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")

    current_user.hashed_password = get_password_hash(new_password)
    await session.commit()

    return MessageResponse(message="密码修改成功")


@router.get("/me/global-filter", response_model=GlobalFilterResponse | None)
async def get_global_filter(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    return current_user.global_filter


@router.post("/me/global-filter", response_model=GlobalFilterResponse, status_code=status.HTTP_201_CREATED)
async def create_global_filter(
    filter_create: GlobalFilterCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    if current_user.global_filter:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="全局过滤器已存在，请使用更新接口")

    filter_obj = GlobalFilter(
        user_id=current_user.id,
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


@router.put("/me/global-filter", response_model=GlobalFilterResponse)
async def update_global_filter(
    filter_update: GlobalFilterUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    if not current_user.global_filter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="全局过滤器不存在，请先创建")

    update_data = filter_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user.global_filter, field, value)

    await session.commit()
    await session.refresh(current_user.global_filter)

    return current_user.global_filter


@router.delete("/me/global-filter", response_model=MessageResponse)
async def delete_global_filter(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    if not current_user.global_filter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="全局过滤器不存在")

    await session.delete(current_user.global_filter)
    await session.commit()

    return MessageResponse(message="全局过滤器已删除")
