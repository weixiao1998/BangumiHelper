from fastapi import APIRouter

from app.api.endpoints import auth, bangumi, health, invite_codes, rss, settings, subscription, user

api_router = APIRouter()

api_router.include_router(health.router, tags=["健康检查"])
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(user.router, prefix="/users", tags=["用户"])
api_router.include_router(bangumi.router, prefix="/bangumi", tags=["番剧"])
api_router.include_router(subscription.router, prefix="/subscriptions", tags=["订阅"])
api_router.include_router(rss.router, prefix="/rss", tags=["RSS"])
# 旧版单订阅 RSS 路径兼容（原 /downloaders/rss/...），后续版本可移除
api_router.include_router(rss.legacy_router, prefix="/downloaders", tags=["RSS(兼容)"])
api_router.include_router(settings.router, prefix="/settings", tags=["系统设置"])
api_router.include_router(invite_codes.router, prefix="/invite-codes", tags=["邀请码"])
