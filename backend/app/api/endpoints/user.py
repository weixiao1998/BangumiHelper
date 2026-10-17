import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_active_user
from app.core.database import get_async_session
from app.models.models import User
from app.schemas import MessageResponse, UserResponse, UserRssTokenResponse

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


@router.get("/me/rss-token", response_model=UserRssTokenResponse)
async def get_user_rss_token(
    current_user: User = Depends(get_current_active_user),
):
    return UserRssTokenResponse(rss_token=current_user.rss_token)


@router.post("/me/rss-token", response_model=UserRssTokenResponse)
async def regenerate_user_rss_token(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    current_user.rss_token = secrets.token_hex(32)
    await session.commit()
    return UserRssTokenResponse(rss_token=current_user.rss_token)
