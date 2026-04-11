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

## 快速命令

```bash
# 后端本地开发
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 18001
ruff check . --fix                # lint + 自动修复
bash migrate.sh upgrade           # 升级数据库

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
backend/app/
├── main.py                  # FastAPI 入口, CORS, lifespan 建表
├── core/
│   ├── config.py            # pydantic-settings 读 .env
│   ├── database.py          # 异步 SQLAlchemy + aiosqlite
│   ├── security.py          # JWT + bcrypt
│   ├── scheduler.py         # APScheduler 定时任务
│   └── constants.py         # 常量
├── models/models.py         # 所有 SQLAlchemy 模型 (单文件)
├── schemas/schemas.py       # 所有 Pydantic schema (单文件)
├── api/endpoints/           # 路由: auth, user, bangumi, subscription, downloader, health, invite_codes
└── services/
    ├── data_sources/        # 插件化数据源: base, mikan, bangumi_moe, dmhy
    └── downloaders/         # 插件化下载器: base, qbittorrent, transmission, aria2

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
- **插件模式**: 数据源/下载器 → 继承抽象基类 → `__init__.py` 注册字典 → 工厂函数获取
- **单文件模型**: `models/models.py`; 所有 Pydantic schema 在 `schemas/schemas.py`
- **前端自动导入**: Element Plus 组件/图标无需手动 import
- **Lint**: Ruff line-length=120, target=py313, 忽略 E501
- **认证**: JWT, 首个注册用户自动成为管理员

## 新增数据源/下载器检查清单

1. 在 `services/data_sources/` 或 `services/downloaders/` 下新建文件，继承 `BaseDataSource` 或 `BaseDownloader`
2. 实现所有抽象方法
3. 在对应 `__init__.py` 的注册字典中添加条目
4. 如需新数据库字段: 创建 Alembic 迁移 (`alembic revision --autogenerate -m "desc"`)，然后 `bash migrate.sh upgrade`
5. 更新 `schemas/schemas.py` 如需新 schema

## 详细文档索引

| 主题 | 路径 |
|------|------|
| Docker 生产部署、Caddy 配置、数据源刷新 | [documents/deployment.md](documents/deployment.md) |
| 运维操作（宿主机 sqlite3 操作数据库等） | [documents/operations.md](documents/operations.md) |
