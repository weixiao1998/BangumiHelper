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

    # fastapi 旧版会把 include_router(prefix="/api") 展开成一系列 /api/... 的 APIRoute；
    # 新版(0.140+) 用懒加载的 _IncludedRouter(path=None) 表示。两者都视为路由已挂载，
    # 因此这里只校验「除了框架内置路由外，确实挂载了自定义路由」，不依赖 /api 前缀的展开形式。
    default_paths = {'/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc'}
    custom = [r for r in app.routes if getattr(r, 'path', None) not in default_paths]
    assert custom, "app 未挂载任何自定义路由"
