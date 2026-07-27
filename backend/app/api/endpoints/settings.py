from fastapi import APIRouter, Depends, HTTPException, status

from app.api.endpoints.auth import get_current_active_user
from app.core.constants import RegistrationMode
from app.core.system_config import SystemConfig
from app.models.models import User
from app.schemas import SystemSettingsResponse, SystemSettingsUpdate

router = APIRouter()


async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user


def _to_response(cfg) -> SystemSettingsResponse:
    return SystemSettingsResponse(
        mikan_url=cfg.mikan_url,
        mikan_username=cfg.mikan_username,
        bangumi_moe_url=cfg.bangumi_moe_url,
        dmhy_url=cfg.dmhy_url,
        proxy=cfg.proxy,
        registration_mode=cfg.registration_mode,
    )


@router.get("/system", response_model=SystemSettingsResponse)
async def get_system_settings(_: User = Depends(get_current_admin_user)):
    cfg = await SystemConfig.get()
    return _to_response(cfg)


@router.put("/system", response_model=SystemSettingsResponse)
async def update_system_settings(
    data: SystemSettingsUpdate,
    _: User = Depends(get_current_admin_user),
):
    update_data = data.model_dump(exclude_unset=True)
    # registration_mode 校验
    if "registration_mode" in update_data and not RegistrationMode.is_valid(update_data["registration_mode"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的注册模式")
    # 密码留空表示不修改
    if update_data.get("mikan_password") == "":
        update_data.pop("mikan_password")
    cfg = await SystemConfig.update(update_data)
    return _to_response(cfg)
