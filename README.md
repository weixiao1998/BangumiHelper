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
| 后端 | FastAPI + Python 3.14 + SQLAlchemy + SQLite + uv |
| 前端 | Vue 3 + Vite + Element Plus + TypeScript |
| 部署 | Docker + Docker Compose |

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd BangumiHelper

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 SECRET_KEY

# 3. 启动服务
docker compose up -d --build

# 4. 访问网站
# http://localhost:8081
```

### 方式二：本地开发

#### 后端

```bash
cd backend

# 创建虚拟环境并安装依赖（使用 uv）
uv venv --python 3.14
source .venv/bin/activate  # Linux/macOS
uv sync --extra dev

# 配置环境变量
export SECRET_KEY="your-secret-key"
export DATABASE_URL="sqlite+aiosqlite:///./data/bangumi.db"

# 启动服务
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端

```bash
cd frontend

# 安装 pnpm（如果没有）
npm install -g pnpm

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev

# 构建生产版本
pnpm build
```

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `SECRET_KEY` | JWT密钥（必须修改） | - |
| `DATABASE_URL` | 数据库连接 | `sqlite+aiosqlite:///./data/bangumi.db` |
| `MIKAN_URL` | 蜜柑计划地址 | `https://mikanani.me` |
| `MIKAN_USERNAME` | 蜜柑计划用户名 | - |
| `MIKAN_PASSWORD` | 蜜柑计划密码 | - |
| `PROXY` | 代理地址 | - |

### 蜜柑计划登录

蜜柑计划部分资源需要登录才能访问，配置 `MIKAN_USERNAME` 和 `MIKAN_PASSWORD` 即可。

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
│   └── pyproject.toml
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── api/           # API 请求
│   │   ├── router/        # 路由配置
│   │   ├── stores/        # 状态管理
│   │   └── views/         # 页面组件
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml      # Docker 编排
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
