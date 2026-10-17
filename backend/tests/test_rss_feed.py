"""RSS feed 窗口逻辑测试（不连数据库）。

回归点：过滤条件只能在 Python 里判定，所以条数上限不能在 SQL 层下推，
否则最新的若干集若都不匹配过滤条件，会把整个窗口吃掉，feed 明明有命中却返回空。
"""

from sqlalchemy import select

from app.models.models import Episode
from app.services.rss_feed import DEFAULT_WINDOW_DAYS, DEFAULT_WINDOW_LIMIT, apply_window, resolve_window


def test_resolve_window_defaults() -> None:
    assert resolve_window() == (DEFAULT_WINDOW_DAYS, DEFAULT_WINDOW_LIMIT)
    assert resolve_window(None, None) == (DEFAULT_WINDOW_DAYS, DEFAULT_WINDOW_LIMIT)


def test_resolve_window_zero_means_unlimited() -> None:
    assert resolve_window(0, 0) == (None, None)
    assert resolve_window(0, 50) == (None, 50)
    assert resolve_window(30, 0) == (30, None)


def test_resolve_window_passthrough() -> None:
    assert resolve_window(7, 20) == (7, 20)


def test_apply_window_filters_by_days_and_orders_desc() -> None:
    sql = str(apply_window(select(Episode), 60))
    assert "publish_time IS NOT NULL" in sql
    assert "publish_time >=" in sql
    assert "ORDER BY episodes.publish_time DESC" in sql


def test_apply_window_without_days_has_no_time_filter() -> None:
    sql = str(apply_window(select(Episode), None))
    assert "publish_time >=" not in sql
    assert "ORDER BY episodes.publish_time DESC" in sql


def test_limit_is_never_pushed_into_sql() -> None:
    """limit 必须在过滤后于 Python 侧截断，SQL 里不应出现 LIMIT。"""
    for days in (None, 60):
        assert "LIMIT" not in str(apply_window(select(Episode), days)).upper()


def test_build_feed_emits_torrent_enclosure() -> None:
    """历史 bug：feedgenerator 的参数名是 enclosures（复数）且属性必须为字符串，
    传单数 enclosure= 会被静默吞掉，导致 feed 里没有 <enclosure>，客户端无法自动下载。"""
    from datetime import UTC, datetime

    from app.models.models import Episode
    from app.services.rss_feed import build_feed

    ep = Episode(
        id=123,
        bangumi_id=1,
        title="测试剧集",
        episode_number=3,
        torrent_url="https://example.com/a.torrent",
        magnet_url="magnet:?xt=urn:btih:abc",
        file_size=None,
        subtitle_group="LoliHouse",
        publish_time=datetime(2026, 9, 12, 10, 0, tzinfo=UTC),
    )

    xml = build_feed(title="t", link="https://example.com", description="d", entries=[(None, ep)])

    # feedgenerator 会按属性名字母序输出，这里只校验内容
    assert "<enclosure " in xml
    assert 'url="https://example.com/a.torrent"' in xml
    assert 'length="0"' in xml
    assert 'type="application/x-bittorrent"' in xml
    assert "<guid>episode-123</guid>" in xml
    assert "<link>magnet:?xt=urn:btih:abc</link>" in xml


def test_build_feed_without_torrent_has_no_enclosure() -> None:
    from app.models.models import Episode
    from app.services.rss_feed import build_feed

    ep = Episode(
        id=124, bangumi_id=1, title="只有磁力", episode_number=4,
        torrent_url=None, magnet_url="magnet:?xt=urn:btih:def", file_size=None,
    )

    xml = build_feed(title="t", link="https://example.com", description="d", entries=[("番剧名", ep)])

    assert "<enclosure" not in xml
    assert "<title>[番剧名] 只有磁力</title>" in xml


def test_collect_feed_entries_dedupes_and_applies_each_subscription_filter() -> None:
    """同一番剧在多个组时：任一订阅命中即输出，但同一集只出现一次。"""
    from types import SimpleNamespace

    from app.models.models import BangumiFilter, Episode
    from app.services.rss_feed import collect_feed_entries

    bangumi = SimpleNamespace(name="番剧A")
    sub1 = SimpleNamespace(id=1, bangumi=bangumi)
    sub2 = SimpleNamespace(id=2, bangumi=bangumi)
    subscriptions_by_bangumi = {1: [sub1, sub2]}
    active_filters = {
        1: BangumiFilter(
            subscription_id=1, user_id=1, bangumi_name="番剧A", subtitle_groups="LoliHouse"
        ),
        2: BangumiFilter(
            subscription_id=2, user_id=1, bangumi_name="番剧A", exclude_keywords="1080p"
        ),
    }

    episodes = [
        Episode(
            id=1,
            bangumi_id=1,
            title="[LoliHouse] 01 [720p][简体]",
            episode_number=1,
            subtitle_group="LoliHouse",
        ),
        Episode(
            id=2,
            bangumi_id=1,
            title="[Other] 02 [720p][简体]",
            episode_number=2,
            subtitle_group="Other",
        ),
        Episode(
            id=3,
            bangumi_id=1,
            title="[Other] 03 [1080p][简体]",
            episode_number=3,
            subtitle_group="Other",
        ),
    ]

    entries = collect_feed_entries(episodes, subscriptions_by_bangumi, active_filters)

    # ep1 两条订阅都命中 → 仍只输出一次；ep2 仅 sub2 命中；ep3 被 sub2 的 1080p 排除
    assert [ep.id for _, ep in entries] == [1, 2]
    assert all(prefix == "番剧A" for prefix, _ in entries)


def test_collect_feed_entries_without_rules_keeps_all() -> None:
    from types import SimpleNamespace

    from app.models.models import Episode
    from app.services.rss_feed import collect_feed_entries

    sub = SimpleNamespace(id=1, bangumi=SimpleNamespace(name="番剧A"))
    episodes = [
        Episode(id=1, bangumi_id=1, title="第 1 集", episode_number=1),
        Episode(id=2, bangumi_id=1, title="第 2 集", episode_number=2),
    ]

    entries = collect_feed_entries(episodes, {1: [sub]}, {1: None})

    assert [ep.id for _, ep in entries] == [1, 2]
