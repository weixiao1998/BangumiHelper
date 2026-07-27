from app.core.system_config import SystemConfig
from app.services.data_sources.bangumi_moe import BangumiMoeDataSource
from app.services.data_sources.base import BaseDataSource
from app.services.data_sources.dmhy import DmhyDataSource
from app.services.data_sources.mikan import MikanDataSource

_data_sources = {
    "mikan": MikanDataSource,
    "dmhy": DmhyDataSource,
    "bangumi_moe": BangumiMoeDataSource,
}


async def get_data_source(source_name: str) -> BaseDataSource:
    source_class = _data_sources.get(source_name)
    if not source_class:
        raise ValueError(f"Unknown data source: {source_name}")
    cfg = await SystemConfig.get()
    return source_class(cfg)


def get_available_data_sources() -> list[str]:
    return list(_data_sources.keys())
