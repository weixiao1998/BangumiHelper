from datetime import UTC, datetime, timedelta, timezone

BEIJING_TZ = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    return datetime.now(UTC)


def beijing_to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BEIJING_TZ)
    return dt.astimezone(UTC)
