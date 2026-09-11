"""过滤规则来源（inherit / custom）语义测试。

方案 1：一个订阅只有一份生效规则，互斥不叠加。
"""

from app.core.constants import FilterMode
from app.core.filter_utils import describe_source, filter_episodes, has_conditions, select_filter
from app.models.models import BangumiFilter, Episode, GlobalFilter


def _episode(**kwargs) -> Episode:
    base = {
        "id": 1,
        "bangumi_id": 1,
        "title": "[LoliHouse] 测试番 / Test - 03 [WebRip 1080p][简体]",
        "episode_number": 3,
        "subtitle_group": "LoliHouse",
    }
    base.update(kwargs)
    return Episode(**base)


def test_select_filter_custom_uses_subscription_rule() -> None:
    sub_rule = BangumiFilter(subscription_id=1, user_id=1, bangumi_name="x", subtitle_groups="LoliHouse")
    global_rule = GlobalFilter(user_id=1, subtitle_groups="OtherGroup")

    assert select_filter(sub_rule, global_rule, FilterMode.CUSTOM) is sub_rule


def test_select_filter_inherit_uses_global_rule() -> None:
    sub_rule = BangumiFilter(subscription_id=1, user_id=1, bangumi_name="x", subtitle_groups="LoliHouse")
    global_rule = GlobalFilter(user_id=1, subtitle_groups="OtherGroup")

    assert select_filter(sub_rule, global_rule, FilterMode.INHERIT) is global_rule
    # 未设置模式时按默认（继承）处理
    assert select_filter(sub_rule, global_rule, None) is global_rule


def test_select_filter_is_mutually_exclusive_not_and() -> None:
    """关键回归：自定义模式下全局规则不参与判定（此前是硬 AND，无法开例外）。"""
    sub_rule = BangumiFilter(subscription_id=1, user_id=1, bangumi_name="x", subtitle_groups="LoliHouse")
    global_rule = GlobalFilter(user_id=1, exclude_keywords="1080p")

    active = select_filter(sub_rule, global_rule, FilterMode.CUSTOM)
    assert active is sub_rule
    # 全局排除 1080p，但自定义模式下列表里仍是命中订阅规则的剧集
    assert len(filter_episodes([_episode()], active)) == 1


def test_select_filter_returns_none_when_nothing_configured() -> None:
    assert select_filter(None, None, FilterMode.INHERIT) is None
    assert select_filter(None, None, FilterMode.CUSTOM) is None


def test_empty_rule_means_no_filtering() -> None:
    """空规则（无条件）等同于不过滤：允许"自定义 + 无条件"显式表达"这个订阅不做过滤"。"""
    empty_sub_rule = BangumiFilter(subscription_id=1, user_id=1, bangumi_name="x")
    empty_global_rule = GlobalFilter(user_id=1)

    assert has_conditions(empty_sub_rule) is False
    assert select_filter(empty_sub_rule, None, FilterMode.CUSTOM) is None
    assert select_filter(None, empty_global_rule, FilterMode.INHERIT) is None
    # 来源也应报 none，而不是"已过滤"
    assert describe_source(empty_sub_rule, None, FilterMode.CUSTOM) == "none"
    assert describe_source(None, empty_global_rule, FilterMode.INHERIT) == "none"
    # 不过滤 = 全部保留
    assert len(filter_episodes([_episode(id=1), _episode(id=2)], None)) == 2


def test_has_conditions_detects_any_field() -> None:
    assert has_conditions(GlobalFilter(user_id=1, min_episode=0)) is True
    assert has_conditions(GlobalFilter(user_id=1, exclude_keywords="480p")) is True
    assert has_conditions(BangumiFilter(subscription_id=1, user_id=1, bangumi_name="x", language="生肉")) is True
    assert has_conditions(None) is False


def test_describe_source() -> None:
    sub_rule = BangumiFilter(subscription_id=1, user_id=1, bangumi_name="x", subtitle_groups="LoliHouse")
    global_rule = GlobalFilter(user_id=1, subtitle_groups="LoliHouse")

    assert describe_source(sub_rule, global_rule, FilterMode.CUSTOM) == "custom"
    assert describe_source(sub_rule, global_rule, FilterMode.INHERIT) == "global"
    assert describe_source(None, global_rule, FilterMode.CUSTOM) == "none"
    assert describe_source(None, None, FilterMode.INHERIT) == "none"


def test_global_filter_supports_language() -> None:
    """全局规则此前缺 language 字段，导致无法全局按语言筛选。"""
    global_rule = GlobalFilter(user_id=1, language="简体中字")
    matched = filter_episodes([_episode(id=1)], global_rule)
    assert [ep.id for ep in matched] == [1]

    # 生肉规则不应命中带「简体」的标题
    raw_rule = GlobalFilter(user_id=1, language="生肉")
    assert filter_episodes([_episode(id=2)], raw_rule) == []


def test_filter_episodes_without_rule_keeps_all() -> None:
    episodes = [_episode(id=1), _episode(id=2)]
    assert filter_episodes(episodes, None) == episodes
