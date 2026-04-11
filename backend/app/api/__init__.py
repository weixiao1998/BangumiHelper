from fastapi import APIRouter

from app.api.endpoints import auth, bangumi, downloader, health, invite_codes, subscription, user

api_router = APIRouter()

api_router.include_router(health.router, tags=["健康检查"])
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(user.router, prefix="/users", tags=["用户"])
api_router.include_router(bangumi.router, prefix="/bangumi", tags=["番剧"])
api_router.include_router(subscription.router, prefix="/subscriptions", tags=["订阅"])
api_router.include_router(downloader.router, prefix="/downloaders", tags=["下载器"])
api_router.include_router(invite_codes.router, prefix="/invite-codes", tags=["邀请码"])
