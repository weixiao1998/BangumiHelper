from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 仅引导配置：启动前所需，改后需 docker compose up -d 重建容器
    # 运行时可变配置（MIKAN_URL / 蜜柑账号 / 代理 / 注册模式 等）已迁至 DB，由管理 UI 维护
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "BangumiHelper"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/bangumi.db"

    DATA_DIR: str = "./data"

    CALENDAR_REFRESH_INTERVAL: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
