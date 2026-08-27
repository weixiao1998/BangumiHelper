from datetime import datetime, timezone

from app.core.utils import beijing_to_utc, current_anime_season


def test_beijing_to_utc_naive_treated_as_beijing():
    # 无时区的北京时间按 +8 处理；2024-01-01 00:00 北京 = 2023-12-31 16:00 UTC
    utc = beijing_to_utc(datetime(2024, 1, 1, 0, 0, 0))
    assert utc.year == 2023
    assert utc.month == 12
    assert utc.day == 31
    assert utc.hour == 16


def test_beijing_to_utc_aware_passthrough():
    utc = beijing_to_utc(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    assert utc.hour == 0  # 自带 UTC 时区则直接转


def test_current_anime_season_by_month():
    # 冬：1-3 月
    assert current_anime_season(datetime(2025, 1, 15)) == (2025, "冬")
    assert current_anime_season(datetime(2025, 3, 31)) == (2025, "冬")
    # 春：4-6 月
    assert current_anime_season(datetime(2025, 4, 1)) == (2025, "春")
    assert current_anime_season(datetime(2025, 6, 30)) == (2025, "春")
    # 夏：7-9 月
    assert current_anime_season(datetime(2025, 7, 1)) == (2025, "夏")
    assert current_anime_season(datetime(2025, 9, 30)) == (2025, "夏")
    # 秋：10-12 月
    assert current_anime_season(datetime(2025, 10, 1)) == (2025, "秋")
    assert current_anime_season(datetime(2025, 12, 31)) == (2025, "秋")


def test_current_anime_season_defaults_to_now():
    year, season = current_anime_season()
    assert year > 2000
    assert season in ("春", "夏", "秋", "冬")
