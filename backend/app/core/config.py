from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import RegistrationMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    APP_NAME: str = "BangumiHelper"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/bangumi.db"

    CORS_ORIGINS_STR: str = "http://localhost:5173,http://localhost:3000"

    DATA_DIR: str = "./data"

    MIKAN_URL: str = "https://mikanani.me"
    MIKAN_USERNAME: str = ""
    MIKAN_PASSWORD: str = ""
    BANGUMI_MOE_URL: str = "https://bangumi.moe"
    DMHY_URL: str = "https://share.dmhy.org"

    DEFAULT_DATA_SOURCE: str = "mikan"

    PROXY: str = ""

    REGISTRATION_MODE: str = RegistrationMode.OPEN

    CALENDAR_REFRESH_INTERVAL: int = 1

    @property
    def CORS_ORIGINS(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS_STR.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
