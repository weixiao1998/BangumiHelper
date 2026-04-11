# AGENTS.md

AI agent 操作指南。修改代码前必须阅读。

## 项目

BangumiHelper — 全栈番剧追踪与下载管理应用。聚合蜜柑计划/bangumi.moe/动漫花园数据源，推送至 qBittorrent/Transmission/Aria2。多用户 + JWT 认证，首个注册用户自动成为管理员。

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3.13, FastAPI, async SQLAlchemy + aiosqlite + SQLite, Pydantic v2, Alembic |
| 前端 | Vue 3 + TypeScript, Pinia, Vue Router, Element Plus, Axios, pnpm |
| 部署 | Docker Compose (backend + Caddy 反代 frontend) |

## 命令

```bash
# 后端
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 18001
ruff check .                      # lint
ruff check . --fix                # 自动修复
bash migrate.sh upgrade           # 升级数据库
bash migrate.sh downgrade         # 回滚一个版本
bash migrate.sh history           # 迁移历史
bash migrate.sh current           # 当前版本

# 前端
cd frontend
pnpm dev                          # :18000, bind localhost, /api 代理到 localhost:18001
pnpm build                        # vue-tsc + vite build
pnpm lint                         # eslint --fix

# Docker
cp .env.example .env              # 修改 SECRET_KEY
docker compose up -d --build
```

## 目录结构

```
backend/app/
├── main.py                  # FastAPI 入口, CORS, lifespan 建表
├── core/
│   ├── config.py            # pydantic-settings 读 .env
│   ├── database.py          # 异步 SQLAlchemy + aiosqlite
│   ├── security.py          # JWT (python-jose) + bcrypt (passlib)
│   ├── scheduler.py         # APScheduler 定时任务
│   └── constants.py         # 常量
├── models/models.py         # 所有 SQLAlchemy 模型 (单文件): User, Bangumi, Episode, Subscription, BangumiFilter, DownloaderConfig, DownloadHistory, SubtitleGroup
├── schemas/schemas.py       # 所有 Pydantic schema (单文件), from_attributes=True
├── api/endpoints/           # 路由: auth, user, bangumi, subscription, downloader, health, invite_codes → 统一 /api 前缀
└── services/
    ├── data_sources/        # 插件化数据源
    │   ├── base.py          # BaseDataSource: fetch_bangumi_calendar, fetch_single_bangumi, fetch_episode_of_bangumi, search_by_keyword
    │   ├── mikan.py         # 蜜柑计划
    │   ├── bangumi_moe.py   # bangumi.moe
    │   ├── dmhy.py          # 动漫花园
    │   └── __init__.py      # 注册字典 + get_data_source(name) 工厂
    └── downloaders/         # 插件化下载器
        ├── base.py          # BaseDownloader: test_connection, add_download, get_download_status, remove_download, get_downloads
        ├── qbittorrent.py
        ├── transmission.py
        ├── aria2.py
        └── __init__.py      # 注册字典 + get_downloader(config) 工厂

frontend/src/
├── api/index.ts             # Axios 实例, /api baseURL, token 拦截, 401→login
├── stores/user.ts           # Pinia (组合式), localStorage token
├── router/index.ts          # 认证守卫, MainLayout 需登录, /login+/register 公开
├── views/                   # Calendar, BangumiDetail, Search, Subscriptions, Downloaders, Settings, Login, Register
├── layouts/MainLayout.vue
└── @ 别名 → src/

backend/migrations/          # Alembic 迁移版本
```

## 关键约定

- **API 前缀**: 所有后端路由 `/api` 下; 开发 Vite 代理, 生产 Caddy 反代
- **全异步**: async SQLAlchemy + async 路由
- **配置**: 环境变量 / `.env` (pydantic-settings)
- **插件模式**: 数据源/下载器 → 实现抽象基类 → `__init__.py` 字典注册 → 工厂函数获取
- **单文件模型**: 所有 SQLAlchemy 模型在 `models/models.py`; 所有 Pydantic schema 在 `schemas/schemas.py`
- **前端自动导入**: Element Plus 组件/图标无需手动 import
- **Lint**: Ruff line-length=120, target=py313, 忽略 E501
- **认证**: JWT, 首个注册用户自动成为管理员

## 新增数据源/下载器检查清单

1. 在 `services/data_sources/` 或 `services/downloaders/` 下新建文件，继承 `BaseDataSource` 或 `BaseDownloader`
2. 实现所有抽象方法
3. 在对应 `__init__.py` 的注册字典中添加条目
4. 如需新数据库字段: 创建 Alembic 迁移 (`alembic revision --autogenerate -m "desc"`)，然后 `bash migrate.sh upgrade`
5. 更新 `schemas/schemas.py` 如需新 schema
