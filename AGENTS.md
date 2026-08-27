# AGENTS.md

AI agent 操作指南。修改代码前必须阅读。

## 项目

BangumiHelper — 全栈番剧追踪与下载管理应用。聚合蜜柑计划数据源，推送至 qBittorrent/Transmission/Aria2。多用户 + JWT 认证，首个注册用户自动成为管理员。

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3.14, FastAPI, async SQLAlchemy + aiomysql + MySQL, Pydantic v2, Alembic, uv 包管理 |
| 前端 | Vue 3 + TypeScript, Pinia, Vue Router, Element Plus, Axios, pnpm |
| 部署 | Docker Compose (backend + Caddy 反代 frontend) |

## 快速命令

```bash
# 后端本地开发
cd backend && uv venv --python 3.14 && source .venv/bin/activate
uv sync --extra dev                  # 安装依赖（含开发依赖）
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 18000
uv run ruff check . --fix            # lint + 自动修复
uv run bash migrate.sh upgrade       # 升级数据库

# 前端本地开发
cd frontend
pnpm dev                          # :18001
pnpm build                        # vue-tsc + vite build
pnpm lint                         # eslint --fix

# Docker 生产
docker compose up -d --build          # 构建+启动（有代码/依赖变更时）
docker compose up -d                  # 复用已命名镜像启动（无变更时）
docker compose restart backend        # 改 .env 后重启

# Docker 开发（挂载源码 + 热重载，改代码免重建）
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build  # 首次/依赖变更
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d          # 直接启动
```

## 目录结构速查

```
backend/
├── pyproject.toml            # 项目配置 + 依赖
├── uv.lock                   # uv 锁文件
├── .venv/                    # 虚拟环境 (uv 管理)
└── app/
    ├── main.py               # FastAPI 入口, lifespan 建表
    ├── core/
    │   ├── config.py         # pydantic-settings 读 .env
    │   ├── database.py       # 异步 SQLAlchemy + aiomysql (连接池)
    │   ├── security.py       # JWT + bcrypt
    │   ├── scheduler.py      # APScheduler 定时任务
    │   ├── constants.py      # 常量
    │   ├── system_config.py # 运行时系统配置 (DB + 内存缓存)
    │   └── utils.py          # 工具函数 (时间处理等)
    ├── models/models.py      # 所有 SQLAlchemy 模型 (单文件)
    ├── schemas/schemas.py    # 所有 Pydantic schema (单文件)
    ├── api/endpoints/        # 路由: auth, user, bangumi, subscription, downloader, health, settings, invite_codes
    └── services/
        ├── data_sources/     # 插件化数据源: base, mikan
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
- **包管理**: 使用 uv 管理依赖，`uv.lock` 锁定版本，应该尽量选用维护活跃的依赖
- **插件模式**: 数据源/下载器 → 继承抽象基类 → `__init__.py` 注册字典 → 工厂函数获取
- **单文件模型**: `models/models.py`; 所有 Pydantic schema 在 `schemas/schemas.py`
- **前端自动导入**: Element Plus 组件/图标无需手动 import
- **Lint**: Ruff line-length=120, target=py314, 忽略 E501
- **认证**: JWT, 首个注册用户自动成为管理员
**配置分层**: 引导配置（SECRET_KEY/DB_* 等）在 `.env`，改后需 `up -d` 重建容器；运行时配置（MIKAN_URL/蜜柑账号/代理/注册模式 等）存 DB，由管理 UI「系统设置」维护，即时生效
- **时间处理**: 后端统一使用 UTC 时间存储和传输，前端使用 `dayjs.utc().local()` 转为用户本地时间显示。时间工具函数位于 `app/core/utils.py`

## 详细文档索引

| 主题 | 路径 |
|------|------|
| 开发指南（新增数据源/下载器、时间处理规范、Docker 开发模式） | [documents/development.md](documents/development.md) |
| Docker 生产部署、Caddy 配置、数据源刷新 | [documents/deployment.md](documents/deployment.md) |
| 运维操作（容器内 mysql 操作数据库、换 MIKAN_URL 数据处理等） | [documents/operations.md](documents/operations.md) |

## AGENTS.md 维护

完成任务后，如涉及以下情况，应及时更新本文件：
- 新增关键约定或设计决策
- 修改目录结构
- 新增常用命令
- 变更技术栈或架构
- 发现需要让 AI agent 注意的事项

**原则**：本文件应保持高效简洁，便于 AI agent 快速理解项目结构和约定，避免冗余描述。
