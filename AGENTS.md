# AGENTS.md

AI agent 操作指南。修改代码前必须阅读。

## 项目

BangumiHelper — 全栈番剧追踪与下载管理应用。聚合蜜柑计划/bangumi.moe/动漫花园数据源，推送至 qBittorrent/Transmission/Aria2。多用户 + JWT 认证，首个注册用户自动成为管理员。

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3.14, FastAPI, async SQLAlchemy + aiosqlite + SQLite, Pydantic v2, Alembic, uv 包管理 |
| 前端 | Vue 3 + TypeScript, Pinia, Vue Router, Element Plus, Axios, pnpm |
| 部署 | Docker Compose (backend + Caddy 反代 frontend) |

## 快速命令

```bash
# 后端本地开发
cd backend && uv venv --python 3.14 && source .venv/bin/activate
uv sync --extra dev                  # 安装依赖（含开发依赖）
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 18001
uv run ruff check . --fix            # lint + 自动修复
uv run bash migrate.sh upgrade       # 升级数据库

# 前端本地开发
cd frontend
pnpm dev                          # :18000
pnpm build                        # vue-tsc + vite build
pnpm lint                         # eslint --fix

# Docker
docker compose up -d --build
docker compose restart backend    # 改 .env 后重启
```

## 目录结构速查

```
backend/
├── pyproject.toml            # 项目配置 + 依赖
├── uv.lock                   # uv 锁文件
├── .venv/                    # 虚拟环境 (uv 管理)
└── app/
    ├── main.py               # FastAPI 入口, CORS, lifespan 建表
    ├── core/
    │   ├── config.py         # pydantic-settings 读 .env
    │   ├── database.py       # 异步 SQLAlchemy + aiosqlite
    │   ├── security.py       # JWT + bcrypt
    │   ├── scheduler.py      # APScheduler 定时任务
    │   ├── constants.py      # 常量
    │   └── utils.py          # 工具函数 (时间处理等)
    ├── models/models.py      # 所有 SQLAlchemy 模型 (单文件)
    ├── schemas/schemas.py    # 所有 Pydantic schema (单文件)
    ├── api/endpoints/        # 路由: auth, user, bangumi, subscription, downloader, health, invite_codes
    └── services/
        ├── data_sources/     # 插件化数据源: base, mikan, bangumi_moe, dmhy
        └── downloaders/      # 插件化下载器: base, qbittorrent, transmission, aria2

frontend/src/
├── api/index.ts             # Axios 实例, /api baseURL, token 拦截, 401→login
├── stores/user.ts           # Pinia (组合式), localStorage token
├── router/index.ts          # 认证守卫
├── views/                   # Calendar, BangumiDetail, Search, Subscriptions, Downloaders, Settings, Login, Register
├── layouts/MainLayout.vue
└── @ 别名 → src/
```

## 关键约定

- **API 前缀**: 所有后端路由 `/api` 下
- **全异步**: async SQLAlchemy + async 路由
- **配置**: 环境变量 / `.env` (pydantic-settings)
- **包管理**: 使用 uv 管理依赖，`uv.lock` 锁定版本
- **插件模式**: 数据源/下载器 → 继承抽象基类 → `__init__.py` 注册字典 → 工厂函数获取
- **单文件模型**: `models/models.py`; 所有 Pydantic schema 在 `schemas/schemas.py`
- **前端自动导入**: Element Plus 组件/图标无需手动 import
- **Lint**: Ruff line-length=120, target=py314, 忽略 E501
- **认证**: JWT, 首个注册用户自动成为管理员
- **时间处理**: 后端统一使用 UTC 时间存储和传输，前端使用 `dayjs.utc().local()` 转为用户本地时间显示。时间工具函数位于 `app/core/utils.py`

## 详细文档索引

| 主题 | 路径 |
|------|------|
| 开发指南（新增数据源/下载器、时间处理规范） | [documents/development.md](documents/development.md) |
| Docker 生产部署、Caddy 配置、数据源刷新 | [documents/deployment.md](documents/deployment.md) |
| 运维操作（宿主机 sqlite3 操作数据库等） | [documents/operations.md](documents/operations.md) |

## AGENTS.md 维护

完成任务后，如涉及以下情况，应及时更新本文件：
- 新增关键约定或设计决策
- 修改目录结构
- 新增常用命令
- 变更技术栈或架构
- 发现需要让 AI agent 注意的事项

**原则**：本文件应保持高效简洁，便于 AI agent 快速理解项目结构和约定，避免冗余描述。
