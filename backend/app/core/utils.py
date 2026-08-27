from datetime import UTC, datetime, timedelta, timezone

BEIJING_TZ = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    return datetime.now(UTC)


def beijing_to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BEIJING_TZ)
    return dt.astimezone(UTC)


def current_anime_season(now: datetime | None = None) -> tuple[int, str]:
    """根据当前月份推算正在播放的季度，返回 (year, 春/夏/秋/冬)。

    动画季度按放送起始月划分：
      1-3 月 冬季（冬），4-6 月 春季（春），7-9 月 夏季（夏），10-12 月 秋季（秋）。
    """
    now = now or utc_now()
    month = now.month
    if month in (1, 2, 3):
        season = "冬"
    elif month in (4, 5, 6):
        season = "春"
    elif month in (7, 8, 9):
        season = "夏"
    else:
        season = "秋"
    return now.year, season
