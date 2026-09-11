# 开发指南

## Docker 开发模式

项目提供 `docker-compose.dev.yml` 开发覆盖文件，挂载源码并启用热重载，改代码无需重建镜像。

```bash
# 首次或依赖变更时构建一次
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 之后启动（改代码无需任何命令，热重载自动生效）
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

- 后端：挂载 `backend/app`，uvicorn `--reload` 自动重载
- 前端：挂载 `frontend`，Vite HMR 热更新，访问 `http://localhost:18001`
- 前端 API 代理通过 `API_PROXY_TARGET=http://backend:8000` 指向容器网络内的后端
- 依赖变更（`pyproject.toml` / `pnpm-lock.yaml`）需重新 `--build`

> 生产部署使用 `docker compose up -d --build`（不加载 dev 文件），见 [deployment.md](deployment.md)。

## 本地开发（无 Docker）

适用于 IDE 断点调试、需要原生运行环境的场景。需自行安装 Python 3.14、Node.js、pnpm。

### 后端

```bash
cd backend

# 创建虚拟环境并安装依赖（使用 uv）
uv venv --python 3.14
source .venv/bin/activate  # Linux/macOS
uv sync --extra dev

# 配置环境变量
export SECRET_KEY="your-secret-key"
# 数据库：本地开发需先启动 MySQL（或连接容器 db，把 DB_HOST 改为 127.0.0.1）
export DB_TYPE=mysql
export DB_HOST=127.0.0.1
export DB_USER=bangumi
export DB_PASSWORD=bangumi
export DB_NAME=bangumi

# 启动服务（端口需与前端代理一致，默认 18000）
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 18000
```

### 前端

```bash
cd frontend

# 安装 pnpm（如果没有）
npm install -g pnpm

# 安装依赖
pnpm install

# 启动开发服务器（:18001，代理 /api 到 http://localhost:18000）
pnpm dev
```

> 前端 API 代理目标可通过 `API_PROXY_TARGET` 环境变量覆盖（见 `vite.config.ts`）。

## 新增数据源检查清单

1. 在 `services/data_sources/` 下新建文件，继承 `BaseDataSource`
2. 实现抽象方法：
   - `fetch_bangumi_calendar` - 获取番剧日历
   - `fetch_single_bangumi` - 获取单个番剧详情
   - `fetch_episode_of_bangumi` - 获取番剧剧集列表
   - `search_by_keyword` - 按关键词搜索
3. 时间解析：使用 `beijing_to_utc()` 将数据源时间转为 UTC（如果数据源是北京时间）
4. 在 `services/data_sources/__init__.py` 的 `DATA_SOURCES` 字典中注册
5. 如需新数据库字段：创建 Alembic 迁移
   ```bash
   alembic revision --autogenerate -m "description"
   bash migrate.sh upgrade
   ```
6. 更新 `schemas/schemas.py` 如需新 schema

## RSS feed 与窗口语义

投放方式只有 RSS：服务端生成 feed，用户自己的下载器按间隔拉取。因此服务端**不保存**下载器
地址/凭据，也没有"服务器直推"的接口（原因见 [订阅/自动下载重构设计](auto-download-redesign.md)）。

- 构造逻辑集中在 `services/rss_feed.py`，两个入口都复用它：
  - `GET /api/rss/subscription/{id}?token=` 单订阅 feed
  - `GET /api/rss/user/{user_id}?token=` 用户级聚合 feed
  - 旧路径 `GET /api/downloaders/rss/{id}?token=` 仅作兼容转发，新代码不要使用
- **窗口语义（重要）**：`days`（默认 60）在 SQL 层截取时间范围；`limit`（默认 100）必须在
  **过滤之后**于 Python 侧截断。过滤条件（字幕组/关键词/语言/集数/正则）只能在 Python 判定，
  若把 LIMIT 下推到 SQL，最新的若干集若不匹配过滤条件就会吃掉整个窗口，导致 feed
  "明明有命中却返回空"（实测出现过）。`tests/test_rss_feed.py` 锁住了这一点。
- `unique_id = episode-{id}` 必须保持稳定：客户端据此去重，避免同一集重复下载。
- 暂停语义：`subscriptions.status = 0` 时，单订阅 feed 返回 404（明确失败，避免客户端把空
  feed 误判为"没有更新"），用户级聚合 feed 跳过该订阅。
- token 为两级：用户级 `users.rss_token` 与订阅级 `subscriptions.rss_token`，均可用
  `secrets.token_hex(32)` 重置。

## 时间处理规范

- 后端统一使用 UTC 时间存储和传输
- 数据源解析时间后，使用 `app/core/utils.py` 中的工具函数转换：
  - `utc_now()` - 获取当前 UTC 时间
  - `beijing_to_utc(dt)` - 北京时间转 UTC
- 前端使用 `dayjs.utc(time).local().format()` 转为用户本地时间显示
