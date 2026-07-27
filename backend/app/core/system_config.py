from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.models import SystemSetting
from app.schemas.schemas import SystemSettings


class SystemConfig:
    """运行时系统配置：DB 存储 + 内存缓存，更新时失效。单进程下缓存有效。"""

    _cache: SystemSettings | None = None

    @classmethod
    async def get(cls) -> SystemSettings:
        if cls._cache is not None:
            return cls._cache
        known_keys = set(SystemSettings.model_fields.keys())
        async with async_session_maker() as session:
            result = await session.execute(select(SystemSetting))
            data = {row.key: row.value for row in result.scalars() if row.key in known_keys}
        cls._cache = SystemSettings(**data)
        return cls._cache

    @classmethod
    async def update(cls, update_data: dict[str, str]) -> SystemSettings:
        async with async_session_maker() as session:
            for key, value in update_data.items():
                existing = await session.get(SystemSetting, key)
                if existing:
                    existing.value = value
                else:
                    session.add(SystemSetting(key=key, value=value))
            await session.commit()
        cls._cache = None
        return await cls.get()

    @classmethod
    def invalidate(cls) -> None:
        cls._cache = None
