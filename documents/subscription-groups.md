# 订阅组设计（分组订阅 + 组级过滤 + 组 RSS）

> 状态：**已实施**（迁移 014 + 后端组规则/RSS + 前端「我的订阅」重构）
> 目标：把订阅从「用户平铺」升级为「用户 → 订阅组 → 番剧订阅」，让不同年份/主题的追番互不影响。

## 一、已确认决策

| 事项 | 结论 |
|---|---|
| 开发库存量数据 | 直接清空 `subscriptions` / `bangumi_filters` / `global_filters`；迁移**不做任何回填** |
| 全局过滤 | 移除。改为订阅组维度的组默认规则 |
| 同一番剧多个组 | 允许；同一组内不允许重复 |
| 整组暂停 | 需要 |
| 删除有订阅的组 | 二次确认后级联删除订阅；至少保留一个组 |
| 单订阅 RSS | **删除**：接口、`subscriptions.rss_token`、前端入口全部移除 |
| `/downloaders/rss` 旧路径 | **删除**，不做兼容 |
| 用户级「全部订阅」RSS | **保留**，继续使用 `users.rss_token` |
| 最终 RSS 类型 | **组 RSS + 用户级全部 RSS** |
| 规则语义 | **整份规则二选一**：`inherit` 整份用组规则，`custom` 整份用订阅自身规则；不叠加、不按字段混搭 |

## 二、数据模型

### `subscription_groups`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK users CASCADE | 组归属用户 |
| `name` | String(50) | 组名，同用户内唯一（大小写不敏感） |
| `description` | Text nullable | 可选描述 |
| `status` | Integer default 1 | 1 启用 / 0 暂停 |
| `rss_token` | String(64) nullable, index | 组级 RSS token |
| `include_keywords` | Text nullable | 组默认规则 |
| `exclude_keywords` | Text nullable | |
| `subtitle_groups` | Text nullable | |
| `language` | String(100) nullable | |
| `regex_pattern` | String(500) nullable | |
| `min_episode` | Integer nullable | |
| `max_episode` | Integer nullable | |
| `created_at` / `updated_at` | DateTime | |

约束：`UniqueConstraint(user_id, name)`。

### `subscriptions`

- 新增 `group_id`：FK `subscription_groups.id`，`ondelete=CASCADE`，非空，索引。
- **删除 `rss_token`**（单订阅 RSS 已移除）。
- `filter_mode`、`status` 保留。
- 同一组内 `(group_id, bangumi_id)` 由 API 校验唯一；不同组允许重复。

### `users.rss_token`

保留，用于用户级「全部订阅」feed。

### 移除 `global_filters`

`GlobalFilter` 模型、schema、`/api/users/me/global-filter` 接口全部删除。

## 三、迁移 014（无回填）

文件：`backend/migrations/versions/014_add_subscription_groups.py`。

### 前置条件

```sql
DELETE FROM bangumi_filters;
DELETE FROM subscriptions;
DELETE FROM global_filters;
```

迁移假设这三张表无业务数据，不复制规则、不回填订阅。必须在清空数据后再执行迁移；否则 `subscriptions.group_id` 非空列会添加失败。

### upgrade

1. 创建 `subscription_groups` 表、唯一约束、`rss_token` 索引。
2. 为每个已有用户插入一个空的「默认订阅组」（`status=1`，规则全空，生成 token）。这是初始化，不是回填。
3. `subscriptions` 增加非空 `group_id`，创建 FK 与索引。
4. 删除 `subscriptions.rss_token` 索引与列。
5. 删除 `global_filters` 表。

### downgrade（有损）

只恢复 013 的表结构：重建 `global_filters` 与 `subscriptions.rss_token`，删除 `group_id` 和 `subscription_groups`。不恢复任何数据。

### 新用户注册

`auth.py` 注册成功后自动创建「默认订阅组」并生成组 token。

## 四、过滤语义

### 整份规则二选一

| `filter_mode` | 生效规则 |
|---|---|
| `inherit` | 整份订阅组默认规则 |
| `custom` | 整份订阅自身规则 |

- 互斥、不叠加，也不做字段级混搭。
- 空规则（无任何条件）= 不过滤；`custom` 下条件全空**不会**回落到组规则。
- 组规则变更立即影响组内所有 `inherit` 订阅；`custom` 不受影响。

示例：组规则为「字幕组=ANi、语言=简体、排除=1080p」。

- 订阅 A `inherit` → ANi + 简体 + 排除 1080p。
- 订阅 B `custom` 只写「字幕组=LoliHouse」→ 只生效 LoliHouse，不自动继承简体/排除。
- 订阅 B `custom` 且全空 → 不过滤。

### 后端唯一判定

`app/core/filter_utils.py`：

```python
FilterRule = BangumiFilter | SubscriptionGroup

select_filter(sub_filter, group_filter, mode) -> FilterRule | None
describe_source(sub_filter, group_filter, mode) -> "group" | "custom" | "none"
filter_episodes(episodes, filter_obj) -> list[Episode]
```

`GET /api/subscriptions/{id}/filtering` 返回：

```json
{
  "filter_mode": "inherit",
  "active_source": "group",
  "group_filter_available": true,
  "active_subtitle_groups": "ANi",
  "matched_episode_ids": [1, 2, 3]
}
```

前端只消费该结果，不复制匹配逻辑。

### 有效暂停

```text
effective_paused = subscription.status == 0 or subscription.group.status == 0
```

- 组暂停只影响输出，不修改订阅 `status`。
- 组 feed：组暂停 → 404；组内暂停订阅跳过。
- 用户级全部 feed：暂停组、暂停订阅都跳过。

## 五、RSS

最终只有两类：

| 类型 | 路径 | 范围 | 暂停行为 | token |
|---|---|---|---|---|
| **组 RSS（主入口）** | `/api/rss/group/{group_id}?token=` | 该组内所有启用订阅，每条按自身生效规则 | 组暂停 → 404；组内暂停订阅跳过 | 组 token |
| **用户级全部 RSS** | `/api/rss/user/{user_id}?token=` | 该用户所有启用组中的启用订阅 | 暂停组/暂停订阅跳过 | 用户 token |

### 组 feed

- 按 `id + rss_token` 查组；无效 token 404。
- 组 `status != 1` → 404。
- 标题：`[BangumiHelper] {group.name}`；链接：`/subscriptions?group={group.id}`。
- 组内无启用订阅时返回空 feed（200）。

### 用户级全部 feed

- 同一番剧可能在多个组：按 `bangumi_id -> list[Subscription]` 聚合。
- 一集只要被任一有效订阅命中就输出，且按 `episode.id` 去重。
- 标题/链接保持现状。

### 窗口与去重

- `days`（默认 60）在 SQL 层截取时间范围。
- `limit`（默认 100）在过滤/去重之后于 Python 侧截断。
- `unique_id = episode-{id}` 保持不变。
- 组 feed 与用户 feed 共用 `services/rss_feed.py::collect_feed_entries()`。

### token

- 组 token：创建组、迁移初始化、注册默认组时生成；`POST /api/rss/group/{id}/regenerate` 重置。
- 用户 token：`POST /api/users/me/rss-token` 重置。
- 没有单订阅 token。

## 六、API

### 订阅组

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/subscription-groups` | 当前用户全部组，按创建顺序 |
| `GET` | `/api/subscription-groups/{id}` | 组详情 |
| `POST` | `/api/subscription-groups` | 创建组；自动生成 rss_token |
| `PUT` | `/api/subscription-groups/{id}` | 更新名称/描述/状态/组规则 |
| `DELETE` | `/api/subscription-groups/{id}?delete_subscriptions=false` | 空组直接删；有订阅需 `true` 才级联 |
| `POST` | `/api/rss/group/{id}/regenerate` | 重置组 RSS token |

错误：

- 重名 → 400；
- 状态非 0/1 → 400；
- 删除最后一个组 → 400；
- 有订阅但未传 `delete_subscriptions=true` → 409；
- 组不存在/不属于当前用户 → 404。

### 订阅

- `GET /api/subscriptions?group_id=&bangumi_id=`。
- `POST /api/subscriptions` 必填 `group_id`；同组重复订阅同一番剧 → 400；跨组允许。
- `PUT /api/subscriptions/{id}` 可传 `group_id` 移动订阅；目标组已有同一番剧 → 400。
- `SubscriptionResponse` 增加 `group: {id,name,status}`，移除 `rss_token`。

### 已移除

- `/api/users/me/global-filter` 全部接口。
- `/api/rss/subscription/{id}` 及其 regenerate。
- `/api/downloaders/rss/{id}` 及兼容路由。

## 七、「我的订阅」页面

布局：**左侧订阅组列表 + 右侧当前组内容**。

- 左侧：组名、订阅数、启用/暂停状态；按创建顺序；支持 `?group={id}` 直达；移动端横向滚动。
- 右侧组头部：
  - 组名/描述；
  - 启用/暂停开关；
  - 「组设置」（`SubscriptionGroupDialog`：名称、描述、组默认规则）；
  - 「组 RSS」（展示/复制/重置组 token；暂停时提示 404）；
  - 「删除」（最后一个组禁用；有订阅时二次确认并提示将取消数量）。
- 组规则统一在「组设置」弹窗中查看/编辑；页面上不再重复展示组规则摘要，避免与设置入口重复。
- 订阅卡片：保留封面网格；角标为「组规则 / 自定义过滤 / 已暂停 / 组已暂停」；操作只有「设置」「取消」，不再有单订阅 RSS 按钮。
- 空组提示去番剧日历订阅；无组提示新建订阅组。

### 订阅设置弹窗

- 新增所属组选择；已订阅该番剧的组置灰。
- 规则来源：继承组默认规则 / 自定义规则。
- 编辑模式可移动组、暂停订阅、取消该订阅。
- 新建默认：所选组有规则 → inherit，否则 custom。

### 番剧详情页

- 显示该番剧在各组的订阅；「订阅设置」下拉选择具体组，另有「订阅到其他组」。
- 过滤预览对每个有效启用订阅调用 `/filtering`，取命中集并集；任一订阅不过滤则不做灰显；多来源显示「多组过滤」。
- 取消订阅在编辑弹窗中完成。

### 设置页

- 移除全局过滤 tab。
- 保留用户级「全部订阅」RSS，并提示按组使用「我的订阅」中的组 RSS。

## 八、边界与约定

- 同一番剧可跨组重复订阅；同一组内不允许。
- 每个用户至少保留一个订阅组。
- 组名同用户内唯一（大小写不敏感）。
- 组规则与订阅自定义规则整份二选一。
- 组列表按创建顺序，v1 不提供排序。
- 组 feed / 用户全部 feed 暂不加缓存。
- 不新增 `(group_id, bangumi_id)` 数据库唯一约束，由 API 校验（避免历史脏数据阻塞迁移）。

## 九、非目标

- 单订阅 RSS（已删除）。
- `/downloaders` 旧路径兼容（已删除）。
- 字段级过滤混搭。
- 组排序/拖拽、颜色/图标。
- 组级下载器配置或服务器直推。
- 数据源、调度器、下载器逻辑改动。
