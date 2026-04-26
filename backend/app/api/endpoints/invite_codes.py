import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_active_user
from app.core.database import get_async_session
from app.models.models import InviteCode, User
from app.schemas import InviteCodeCreate, InviteCodeResponse, MessageResponse

router = APIRouter()


def generate_invite_code() -> str:
    return secrets.token_urlsafe(16)


@router.get("", response_model=list[InviteCodeResponse])
async def get_invite_codes(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(InviteCode).where(InviteCode.created_by == current_user.id)
    )
    return result.scalars().all()


@router.post("", response_model=InviteCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_invite_code(
    code_create: InviteCodeCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    code = generate_invite_code()

    expires_at = None
    if code_create.expires_days:
        expires_at = datetime.now() + timedelta(days=code_create.expires_days)

    invite_code = InviteCode(
        code=code,
        created_by=current_user.id,
        max_uses=code_create.max_uses,
        expires_at=expires_at,
    )

    session.add(invite_code)
    await session.commit()
    await session.refresh(invite_code)

    return invite_code


@router.delete("/{code_id}", response_model=MessageResponse)
async def delete_invite_code(
    code_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    result = await session.execute(
        select(InviteCode).where(
            InviteCode.id == code_id, InviteCode.created_by == current_user.id
        )
    )
    invite_code = result.scalar_one_or_none()

    if not invite_code:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邀请码不存在")

    await session.delete(invite_code)
    await session.commit()

    return MessageResponse(message="邀请码删除成功")
