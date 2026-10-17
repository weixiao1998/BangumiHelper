"""订阅组模型与组默认规则的纯模型测试（不连数据库）。"""

from app.core.filter_utils import has_conditions
from app.models.models import SubscriptionGroup


def _group(**kwargs) -> SubscriptionGroup:
    base = {"user_id": 1, "name": "2025 追番"}
    base.update(kwargs)
    return SubscriptionGroup(**base)


def test_empty_group_rule_has_no_conditions() -> None:
    assert has_conditions(_group()) is False


def test_group_rule_detects_any_filter_field() -> None:
    assert has_conditions(_group(include_keywords="简体")) is True
    assert has_conditions(_group(min_episode=0)) is True
    assert has_conditions(_group(regex_pattern=r"第\s*0?1\s*集")) is True


def test_group_default_status_is_enabled() -> None:
    # SQLAlchemy column default 在 flush 时生效，这里校验列定义即可
    assert SubscriptionGroup.__table__.c.status.default.arg == 1
