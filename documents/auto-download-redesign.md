# 订阅 / 自动下载 / 下载器 —— 重构设计稿 v2

> 状态：**决策已定，P1+P2 已实施**（实施记录见文末「六」；P3/P4 待做）
> 前提：**目标形态 = 公网共享实例**（多用户注册，各自的下载器在自家 NAT 后面）
> 结论：**投递只有 RSS**，服务器直推能力**整体删除**。

## 〇、决策日志

| 议题 | 结论 | 说明 |
|---|---|---|
| 目标部署形态 | **公网共享实例为主** | 用户自带家里下载器 |
| 投递模型 | **RSS 为主线** | 原「`auto_download` 布尔 + RSS 独立通道」方案**作废**：公网形态下服务器够不到用户下载器，push 无法作为主线 |
| 设置入口 | 合并为单一「订阅设置」弹窗，创建/编辑共用 | 沿用 v1 结论 |
| 暂停订阅 | 启用 `status` 语义（1 启用 / 0 暂停） | 沿用 v1 结论 |
| 启用基线（补不补历史） | **改由 feed 窗口控制**（服务端） | v1 的"每个订阅单独选"作废：RSS 形态下载由客户端发起，"补历史"本质是"feed 里有没有旧条目" |
| 服务器直推下载器 | **彻底删除** | 已移除下载器管理页、直推接口/服务、`downloader_configs` 与 `download_history` 表、订阅上的直推字段与前端依赖 |
| RSS token 体系 | **保留两级** | 用户级 `users.rss_token` + 订阅级 `subscriptions.rss_token`，可单独重置某个订阅 |
| feed 窗口默认值 | **最近 60 天或 100 条，取先到者** | `?days=` / `?limit=` 可覆盖，`0` 表示不限 |
| 本轮范围 | **P1 + P2** | 数据清理 + RSS 质量；P3（订阅设置弹窗合并、教程引导）与 P4（手动下载交互细化）待做 |

## 一、可行性约束（为什么不能以 push 为主线）

| 通道 | 数据流向 | 穿透 NAT | 公网实例可用性 |
|---|---|---|---|
| RSS | 用户下载器 → 服务器 | ✅ 出站即可 | **主线** |
| 复制 / 打开磁力、下载 .torrent | 浏览器 → 本地客户端 | ✅ 完全本地 | 兜底（普适） |
| 服务器直推下载器 | 服务器 → 用户下载器 | ❌ 需入站可达 | 仅当用户自托管或自行暴露 WebUI（例外） |

实测证据（当前后端容器）：

```
容器内 127.0.0.1:13306 (宿主机映射端口) -> ConnectionRefused   # 容器里的 127.0.0.1 是它自己
host.docker.internal -> 解析失败 (gaierror)                    # Linux 需 compose extra_hosts
下载器表单默认 host = 127.0.0.1                                 # Downloaders.vue:150，对容器化后端是错误默认值
```

推论：**现有的手动"发送到下载器"在公网形态下同样不可用**（它和 push 走同一条 `POST /downloaders/download` 链路），README 的"远程下载管理/选择下载器"没有交代这层前提。

## 二、现状问题

### 因"改为 RSS 主线"而自动消失

- `auto_download` 空开关（`subscription.py:80`，全后端无读取；`scheduler.py:70` 注明"仅入库不触发下载"）
- 订阅级 `downloader_id` / `save_path` 存了不用；`DownloadRequest` 无 `save_path`（`schemas.py:279-282`）
- 保存路径传错参数：`downloader.py:182` 把下载器 `token` 当 `save_path`（aria2 的 token 是 RPC 密钥，`aria2.py:15,28`）
- 订阅后无法修改这些设置（订阅弹窗仅未订阅可开，`BangumiDetail.vue:30-36`）

### 独立存在，仍需修（仅当保留直推，见待确认 1）

- 更新下载器时不清其它默认 → 可造出两个默认 → `scalar_one_or_none()` 抛 `MultipleResultsFound` → 500（已实测）
- qBittorrent 用 `token` 当分类（`qbittorrent.py:37`），但 UI 只在 aria2 下显示 Token（`Downloaders.vue:62`）
- aria2 RPC 兜底路径 `/rpc` 与 UI 占位 `/jsonrpc` 不一致（`aria2.py:12`）

### RSS 主线自身的问题（本设计的主要工作量）

1. **无窗口**：单订阅 feed 输出该番剧**全部**剧集（最长 356 条），用户级 feed 是全部订阅之和。首次添加会把历史全集灌进下载器，也是"补历史"问题的根源。
2. **暂停不生效**：`status` 在两个 feed 里都没被判断。
3. **两套 token**：订阅级 `subscription.rss_token`（`downloader.py:296`）与用户级 `user.rss_token`（`user.py:111`），策略不统一。
4. **实现重复**：`downloader.py:212-293` 与 `rss.py:18-95` 是两段近乎相同的 feed 构造代码。
5. **命名空间归位**：单订阅 feed 挂在 `/downloaders/rss/...` 下，语义上属于 RSS 而非下载器。
6. **无缓存/限流**：每次轮询都全量查库 + Python 过滤 + 拼 XML，公网多用户多订阅时有放大效应。
7. **引导缺失**：RSS 链接藏在按钮后，没有"qBittorrent 怎么加、保存路径/分类在哪设"的说明——而这恰恰是该形态下用户唯一的自动下载配置入口。

数据参考：episodes 17319 条全部同时具备 `torrent_url` 与 `magnet_url`（enclosure 不会缺失）；单番剧最多 356 集、平均 55 集；近 30 天 2541 集。

## 三、目标设计

### 3.1 通道与职责

```
订阅 = 过滤规则（服务端生效）+ 投放通道
  ├─ RSS（主）：服务器出 feed，用户下载器拉取 → 自动下载
  └─ 手动（兜底）：复制/打开 magnet、下载 .torrent → 本地客户端
  └─ 直推（进阶，待定）：服务器 → 下载器，仅当可达
```

**核心卖点要写进 UI**：过滤（关键词/字幕组/语言/集数/正则）全部在**服务端**完成，用户下载器里的 RSS 规则不需要再配关键词——这是相对"直接订阅蜜柑 RSS"的差异化。

### 3.2 数据模型

**`subscriptions`**

- **删**：`auto_download`、`downloader_id`、`save_path`（对公网形态无意义，留着只会继续误导）
- **保留并明确**：`status`（1 启用 / 0 暂停）、`rss_token`
- 迁移后 defunct 列一并清理（现存 6 条订阅、全部 `auto_download=0`、`downloader_id=NULL`，无数据风险）

**不新建 `download_records` / 不启用 `download_history`**

RSS 形态下服务器**无法知道**用户是否真的下载了（投递由客户端发起）。强行记录只会再造一个"存了不用"的字段——这正是本次要消灭的模式。0 行的 `download_history` 建议直接删除。

**`downloader_configs`**：取决于待确认 1。若保留直推，则拆出 `category`（qBittorrent 分类 / Transmission 标签）与 `save_path`（该下载器默认目录），`token` 收窄为仅 aria2 RPC 密钥。

**`BangumiFilter` / `GlobalFilter`**：不变，`filter_episodes()` 继续作为唯一判定入口。

### 3.3 RSS 一等公民化（服务端）

| 项 | 设计 |
|---|---|
| 窗口化 | 默认只输出最近 **60 天**或最近 **100 条**（取先到者）；支持 `?days=` / `?limit=` 覆盖；`limit=0` 表示全量（显式选择才给全量） |
| 暂停 | `status=0` 的订阅在用户级 feed 中跳过；单订阅 feed 返回 404（明确失败，避免客户端把空 feed 当"没更新"静默失败） |
| 幂等/去重 | `unique_id = episode-{id}`（已有 ✅）；enclosure 保证存在（数据实测 ✅，仍加防御分支） |
| 代码归位 | feed 构造抽到 `services/rss_feed.py`，单订阅 feed 路由从 `downloader.py` 移到 `rss.py`，路径改为 `/rss/subscription/{id}` |
| token 策略 | 见待确认 2 |
| 性能 | feed 生成加短 TTL 缓存（60s）或按 `(subscription_id, token)` 缓存；后续按 QPS 再定 |
| 兼容 | 旧路径 `/downloaders/rss/{id}?token=` 保留一个版本做 302/兼容，避免已配置的用户下载器失效 |

### 3.4 前端交互

**A. 订阅设置弹窗（合并"订阅设置" + "过滤器"，创建/编辑共用）**

- 过滤条件（现有字段，含高级项）
- 订阅状态：启用 / 暂停
- **保存后**：直接给出 RSS 链接 + 复制按钮 + 「如何在 qBittorrent / Transmission 里添加」折叠说明
  - 关键提示：保存路径、分类、做种限制等**在下载器的 RSS 规则里设置**，服务端不代管
- 删掉"自动下载开关 / 下载器 / 保存路径"三项

**B. 详情页**

- 已订阅时按钮：「订阅设置」+「RSS 订阅」，替代现在的「过滤器」
- 每集按钮：主操作「复制磁力」/「打开磁力」（`magnet:` 直接唤起本地客户端）+「下载种子」；仅当配置了可达下载器时才显示「发送到下载器」

**C. 我的订阅页**

- 卡片状态行：`已过滤` / `已暂停`；RSS 按钮保留（弹窗内给链接与教程）

**D. 设置页 → RSS 订阅**

- 用户级聚合 feed 已有（`/api/rss/user/{id}?token=`），补充：配置教程、"暂停的订阅不会出现在 feed 里"、token 泄漏处置说明

### 3.5 直推通道（若保留，见待确认 1）

- compose 加 `extra_hosts: ["host.docker.internal:host-gateway"]`
- 下载器表单默认值去掉 `127.0.0.1`，placeholder 改为"必须是**后端容器**能访问的地址（如宿主机局域网 IP）"
- 「测试连接」错误分类提示：DNS 失败 / 连接被拒 / 超时，分别给出针对性建议
- UI 明确标注"仅当服务器能访问该地址时可用"，并放在"进阶"折叠区
- 修 3 个 bug：`save_path` 传 token、默认下载器唯一性、aria2 RPC 默认路径
- 文档补一节"网络可达性"

## 四、API 变更清单

| 接口 | 变更 |
|---|---|
| `GET /subscriptions` | 移除 `auto_download` / `downloader_id` / `save_path`；保留 `status`、`rss_token` |
| `PUT /subscriptions/{id}` | 围绕"过滤条件 + status"组织；删掉死字段 `current_episode`（`schemas.py:153`） |
| `POST /subscriptions/{id}/rss-token` | 新增：生成/重置该订阅 feed token（替代挂在 `/downloaders/rss/{id}/regenerate`） |
| `GET /rss/subscription/{id}?token=&days=&limit=` | 新增（由 `/downloaders/rss/{id}` 归位而来，旧路径保留兼容） |
| `GET /rss/user/{id}?token=&days=&limit=` | 增加窗口参数；跳过暂停订阅 |
| `POST /downloaders/download` | 仅当保留直推时调整（`save_path` / `category`） |

## 五、实施分期

| 期 | 内容 | 说明 |
|---|---|---|
| **P1** | 数据与清理：迁移删 `auto_download`/`downloader_id`/`save_path`、启用 `status` 暂停语义、清理死字段 | 消除误导源头 |
| **P2** | RSS 质量：窗口化、暂停过滤、去重/guid 校验、两处实现合并、路由归位、缓存、旧路径兼容 | 本设计的核心 |
| **P3** | 前端：订阅设置弹窗合并、保存后 RSS 引导与教程、详情页/卡片/设置页改造 | 用户可感知的主要收益 |
| **P4** | 手动下载交互：`magnet:` 直开、复制、.torrent；README 修正 | 公网形态下的正确兜底 |
| **P5** | （可选）直推通道处置：连通性修复 + category/save_path + 文档 | 取决于待确认 1 |

## 六、实施记录（P1 + P2，已完成）

**P1 数据与清理**

- 迁移 `012_remove_downloaders.py`：删除 `downloader_configs`、`download_history` 两张表与
  `subscriptions.auto_download / downloader_id / save_path` 三列（FK 名由数据库生成，迁移里
  用 inspector 读真实名后再删，MySQL / PostgreSQL 通用）。测试环境已执行，当前版本 `012`。
- 删除后端：`api/endpoints/downloader.py`、`services/downloaders/`（qbittorrent/transmission/aria2）、
  `DownloaderConfig` / `DownloadHistory` 模型、下载器与 `DownloadRequest` 相关 schema、
  `downloader` 路由注册；顺带清理死字段 `SubscriptionUpdate.current_episode`。
- 删除依赖：`qbittorrent-api`、`transmission-rpc`（`uv.lock` 已重生成）。
- 删除前端：`views/Downloaders.vue`、路由与侧边栏入口、`downloaderApi`、详情页订阅弹窗中的
  自动下载/下载器/保存路径三项。
- 暂停语义：`status=0` 的单订阅 feed 返回 404，用户级聚合 feed 跳过；订阅卡片显示「已暂停」
  角标，RSS 弹窗内提供暂停/启用开关（P3 会把它挪进统一的「订阅设置」弹窗）。

**P2 RSS 质量**

- 新增 `services/rss_feed.py`：feed 构造（`build_feed`）、窗口解析与查询（`resolve_window` /
  `apply_window`），消除了原先 `downloader.py` 与 `rss.py` 两处近乎重复的实现。
- 路由归位：单订阅 feed 由 `/downloaders/rss/{id}` 移到 `/rss/subscription/{id}`，token 重置移到
  `/rss/subscription/{id}/regenerate`；旧路径保留兼容转发（`rss.legacy_router`），已配置的下载器不会失效。
- 窗口：默认最近 60 天或 100 条，`?days=` / `?limit=`（`0` 为不限）覆盖。
- 暂停过滤、稳定 `unique_id`、错误 token 404、`publish_time` 为空的旧数据按窗口排除。
- 测试：`tests/test_rss_feed.py`（窗口解析、SQL 中不得出现 LIMIT 等）。

**实施中发现的坑（已修正并加测试）**

1. **`limit` 不能下推到 SQL**：实测出现"有命中却返回空"——某订阅 60 天窗口内 8 集命中过滤条件，
   但 `limit=3` 时最新 3 集恰好都不是该订阅指定的字幕组与语言，被过滤后 feed 变成 0 条。
   现改为 **`days` 在 SQL 截取、`limit` 在过滤后于 Python 侧截断**。
2. **feed 从来没有 `<enclosure>`（既有 bug）**：`feedgenerator.add_item` 的参数名是
   `enclosures`（复数、`Enclosure` 实例），旧代码传的是单数 `enclosure={...}`，被 `**kwargs`
   静默吞掉。也就是说此前 RSS 只提供磁力 `link`，而 qBittorrent 等客户端的 RSS 自动下载依赖
   enclosure——自动下载很可能一直不生效。现已修正（`Enclosure` 的三个属性还会被直接写入 XML，
   必须传字符串，否则 XML 序列化报 `'int' object has no attribute 'replace'`）。

**有意未做**

- P2 里列的 feed 缓存没有实现：窗口化已把单次查询限定在时间窗口内（实测单番剧 60 天内最多
  百行量级），先不引入缓存以免增加失效逻辑；若公网 QPS 上升，再按 `(subscription_id, token)`
  加 60s TTL 缓存。

**尚未完成（P3 / P4）**

- P3：把「订阅设置」与「过滤器」合并为创建/编辑共用弹窗；保存后直接展示 RSS 链接与
  qBittorrent / Transmission 配置教程；详情页/卡片/设置页的引导改造。
- P4：手动下载交互细化（`magnet:` 协议直接唤起本机客户端等）。当前详情页与搜索页已改为
  「复制磁力 / 下载种子」，不再依赖下载器接口。
