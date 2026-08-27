"""冒烟测试：确保应用能正常导入且为 FastAPI 实例。

导入即触发 app.api / app.core / app.services 的加载，能在依赖升级后
第一时间暴露 import 级别的破坏（如依赖版本断裂）。不连接数据库。
"""


def test_app_imports() -> None:
    from app.main import app

    assert app.title == "BangumiHelper API"
    assert app.version == "1.0.0"


def test_api_router_registered() -> None:
    from app.main import app

    # 路由已挂载到 /api 前缀下（通过 include_router 注入）
    assert any(getattr(r, "path", "").startswith("/api/") for r in app.routes)
