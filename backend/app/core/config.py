from functools import lru_cache
from urllib.parse import quote_plus

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

    # 数据库配置：DB_TYPE 切换 mysql / postgresql，DATABASE_URL 由下方 property 自动拼接对应驱动连接串
    DB_TYPE: str = "mysql"  # mysql | postgresql
    DB_HOST: str = "db"
    DB_PORT: int | None = None  # 留空(None)则按 DB_TYPE 取默认端口（mysql 3306 / postgresql 5432）
    DB_USER: str = "bangumi"
    DB_PASSWORD: str = "bangumi"
    DB_NAME: str = "bangumi"

    DATA_DIR: str = "./data"

    CALENDAR_REFRESH_INTERVAL: int = 1
    EPISODE_REFRESH_INTERVAL: int = 1

    @property
    def DATABASE_URL(self) -> str:
        """按 DB_TYPE 拼接数据库连接串；用户名/密码做 URL 编码以兼容特殊字符。"""
        user = quote_plus(self.DB_USER)
        password = quote_plus(self.DB_PASSWORD)
        if self.DB_TYPE == "mysql":
            port = self.DB_PORT or 3306
            return f"mysql+aiomysql://{user}:{password}@{self.DB_HOST}:{port}/{self.DB_NAME}?charset=utf8mb4"
        if self.DB_TYPE == "postgresql":
            port = self.DB_PORT or 5432
            return f"postgresql+asyncpg://{user}:{password}@{self.DB_HOST}:{port}/{self.DB_NAME}"
        raise ValueError(f"不支持的 DB_TYPE: {self.DB_TYPE}（仅支持 mysql / postgresql）")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
