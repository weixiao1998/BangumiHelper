from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import RegistrationMode
from app.core.database import get_async_session
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.models import InviteCode, User
from app.schemas import RegistrationConfigResponse, Token, UserCreate, UserResponse

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    from app.core.security import decode_access_token

    username = decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已被禁用")
    return current_user


@router.get("/registration-config", response_model=RegistrationConfigResponse)
async def get_registration_config():
    mode = settings.REGISTRATION_MODE
    message_map = {
        RegistrationMode.OPEN: "注册开放",
        RegistrationMode.CLOSED: "注册已关闭",
        RegistrationMode.INVITE_ONLY: "需要邀请码才能注册"
    }
    return RegistrationConfigResponse(mode=mode, message=message_map.get(mode, "未知模式"))


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: UserCreate,
    session: AsyncSession = Depends(get_async_session),
):
    if settings.REGISTRATION_MODE == RegistrationMode.CLOSED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="注册已关闭")

    if settings.REGISTRATION_MODE == RegistrationMode.INVITE_ONLY:
        if not user_create.invite_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="需要邀请码才能注册")

        result = await session.execute(
            select(InviteCode).where(InviteCode.code == user_create.invite_code)
        )
        invite_code = result.scalar_one_or_none()

        if not invite_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的邀请码")

        if invite_code.is_used and invite_code.current_uses >= invite_code.max_uses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邀请码已使用完毕")

        if invite_code.expires_at and invite_code.expires_at < datetime.now():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邀请码已过期")

    result = await session.execute(select(User).where(User.username == user_create.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

    result = await session.execute(select(User).where(User.email == user_create.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被注册")

    user = User(
        username=user_create.username,
        email=user_create.email,
        hashed_password=get_password_hash(user_create.password),
    )

    result = await session.execute(select(User))
    if result.scalar_one_or_none() is None:
        user.is_admin = True

    session.add(user)
    await session.commit()
    await session.refresh(user)

    if settings.REGISTRATION_MODE == RegistrationMode.INVITE_ONLY and user_create.invite_code:
        result = await session.execute(
            select(InviteCode).where(InviteCode.code == user_create.invite_code)
        )
        invite_code = result.scalar_one_or_none()
        if invite_code:
            invite_code.current_uses += 1
            if invite_code.current_uses >= invite_code.max_uses:
                invite_code.is_used = True
            invite_code.used_by = user.id
            invite_code.used_at = datetime.now()
            await session.commit()

    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已被禁用")

    access_token = create_access_token(subject=user.username, expires_delta=timedelta(days=7))

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
