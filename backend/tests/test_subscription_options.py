"""回归测试：订阅接口查询选项必须覆盖响应模型依赖的关系。

背景：BangumiResponse 新增 seasons 字段后，/api/subscriptions 只预加载了
Subscription.bangumi.episodes，响应序列化时访问未加载的 bangumi.seasons 会在异步
上下文之外触发懒加载（MissingGreenlet），最终 500（订阅页打不开）。

本测试不连接数据库，只校验查询选项覆盖了 SubscriptionResponse 需要的关系，
避免同类问题再次出现。
"""

from app.api.endpoints.subscription import SUBSCRIPTION_BASE_OPTIONS


def _option_paths() -> set[str]:
    return {str(option.path) for option in SUBSCRIPTION_BASE_OPTIONS}


def test_subscription_options_preload_response_relations() -> None:
    paths = _option_paths()

    # SubscriptionResponse.bangumi -> BangumiResponse：需要 episodes 与 seasons
    for relation in ("Bangumi.episodes", "Bangumi.seasons"):
        assert any(relation in path for path in paths), (
            f"订阅查询未预加载 {relation}，响应序列化会触发懒加载并返回 500"
        )

    # SubscriptionResponse.filter
    assert any("Subscription.filter" in path for path in paths), "订阅查询未预加载 Subscription.filter"
