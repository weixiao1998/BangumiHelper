# BangumiHelper - 追番助手

一个现代化的追番助手网站，支持多数据源、多用户、远程下载管理。

## ✨ 功能特性

- 📺 **番剧日历** - 按星期展示当季番剧列表
- 🔍 **多数据源** - 支持蜜柑计划、bangumi.moe、动漫花园
- 📥 **下载管理** - 支持 qBittorrent、Transmission、Aria2 远程下载
- 🔗 **多种下载方式** - 磁力链接、种子文件、RSS订阅
- 👥 **多用户系统** - 用户注册登录，数据隔离
- 🎯 **智能过滤** - 支持关键词、字幕组、正则过滤

## 🛠 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | FastAPI + Python 3.14 + SQLAlchemy + MySQL (aiomysql) + uv |
| 前端 | Vue 3 + Vite + Element Plus + TypeScript |
| 部署 | Docker + Docker Compose |

## 🚀 快速开始

### Docker 开发（推荐）

无需本地安装 Python / Node 环境，一条命令启动带热重载的开发环境。

```bash
# 1. 克隆项目
git clone <repository-url>
cd BangumiHelper

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 SECRET_KEY

# 3. 启动开发环境（首次或依赖变更时加 --build）
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 4. 访问开发服务（改代码自动热重载）
# http://localhost:18001
```

> 生产部署：`docker compose up -d --build`，访问 `http://localhost:8001`，详见 [部署文档](documents/deployment.md)。

### 本地开发（无 Docker）

适用于 IDE 断点调试等场景，需自行安装 Python 3.14 / Node / pnpm，命令见 [开发指南](documents/development.md#本地开发无-docker)。

## ⚙️ 配置说明

### 引导配置（.env 文件）

改后需 `docker compose up -d` 重建容器生效：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `SECRET_KEY` | JWT密钥（必须修改） | - |
| `DB_TYPE` | 数据库类型（mysql / postgresql） | `mysql` |
| `DB_HOST` / `DB_USER` / `DB_PASSWORD` | 数据库主机 / 账号 / 密码 | `db` / `bangumi` / `bangumi` |
| `DB_NAME` | 数据库名 | `bangumi` |
| `CALENDAR_REFRESH_INTERVAL` | 番剧日历刷新间隔（小时） | `1` |

### 运行时配置（管理 UI）

蜜柑URL、蜜柑账号密码、代理地址、注册模式等运行时配置，登录管理员账号后在「设置 → 系统配置」页面修改，保存后即时生效，无需重启容器。

## 📖 使用指南

### 首次使用

1. 访问网站，点击注册
2. 第一个注册的用户自动成为管理员
3. 管理员在「设置」页面刷新番剧列表

### 订阅番剧

1. 在首页番剧日历中找到想追的番剧
2. 点击番剧卡片进入详情页
3. 点击「订阅」按钮

### 配置下载器

1. 进入「下载器管理」页面
2. 添加下载器（qBittorrent / Transmission / Aria2）
3. 测试连接确保可用
4. 设为默认下载器

### 下载番剧

1. 进入番剧详情页
2. 选择要下载的剧集
3. 点击下载按钮
4. 选择下载器或复制链接

## 📁 项目结构

```
BangumiHelper/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # 数据模式
│   │   ├── services/       # 业务逻辑
│   │   │   ├── data_sources/  # 数据源爬虫
│   │   │   └── downloaders/   # 下载器集成
│   │   └── main.py         # 应用入口
│   ├── Dockerfile
│   ├── .dockerignore
│   └── pyproject.toml
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── api/           # API 请求
│   │   ├── router/        # 路由配置
│   │   ├── stores/        # 状态管理
│   │   └── views/         # 页面组件
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml      # Docker 编排（生产）
├── docker-compose.dev.yml  # Docker 编排（开发，热重载）
├── .env.example            # 环境变量示例
└── README.md
```

## 🔧 开发命令

```bash
# 后端
cd backend
uv sync --extra dev         # 安装依赖（含开发依赖）
uv run pytest               # 运行测试
uv run ruff check . --fix   # 代码检查 + 自动修复
uv run mypy .               # 类型检查

# 前端
cd frontend
pnpm dev                    # 开发服务器
pnpm build                  # 构建
pnpm lint                   # 代码检查
```

## 📄 License

MIT License
