# 过滤规则重构设计（全局过滤器 → 默认规则）

> 状态：**已实施**（迁移 013 + 后端判定收敛 + 前端改造）
> 起因：全局过滤器与订阅过滤器是硬 AND 叠加，既无法为单个订阅开例外，也存在前后端两份判定实现。

## 一、原设计的问题（均已复现）

| # | 问题 | 证据 |
|---|---|---|
| 1 | **硬 AND 叠加、无例外通道**：全局放一个 `include_keywords` 会卡死所有订阅；全局排除「繁中」，某个订阅想要繁中就做不到 | 旧 `filter_episodes` = `匹配(全局) and 匹配(订阅)` |
| 2 | **前端复制了一份判定且已跑偏**：详情页 `matchEpisode()` 只看订阅规则，完全不知道全局规则；设置页却写着"应用于 RSS 输出**和剧集列表**" | 实测：订阅规则命中 10 集，加一条全局 `exclude=1080p` 后 RSS 变 0 集，而详情页仍显示 10 集"会下载" |
| 3 | **字段不对称**：`GlobalFilter` 没有 `language`，全局无法按语言筛选；旧代码用 `getattr(filter_obj, "language", None)` 兜着 | `filter_utils.py` |
| 4 | **生效来源不可见**：订阅卡片/详情页的「已过滤」只看 `sub.filter`，只设全局规则时全站无任何提示 | `Subscriptions.vue` / `BangumiDetail.vue` |
| 5 | **同一概念两处实现**：后端 Python 与前端 TS 各一份（连 `LANGUAGE_KEYWORDS` 都复制了），必须手工同步 | `BangumiDetail.matchEpisode` |

## 二、目标语义（方案 1）

一个订阅在任一时刻只有**一份**生效规则：

| `subscriptions.filter_mode` | 生效规则 |
|---|---|
| `inherit`（默认） | 用户的**全局默认规则**（`GlobalFilter`） |
| `custom` | 订阅**自身**的规则（`BangumiFilter`） |

两者互斥、**不叠加**。全局规则的角色从"叠加层"变为"默认值"。

**不变量与约定**

- **空规则（没有任何条件）= 不过滤**：允许"自定义 + 无条件"存在，用来显式表达"这个订阅不做过滤"。
  这种情况下 `/filtering` 的 `active_source` 为 `none`，UI 不显示"已过滤"角标。
- 新建订阅规则 → 自动切到 `custom`；删除订阅规则 → 回落 `inherit`。
- `inherit` 模式下，订阅原有规则**保留但停用**（不删数据），UI 明确提示。

## 三、数据模型与迁移（013）

- `subscriptions.filter_mode`：`varchar(10) not null default 'inherit'`
- `global_filters.language`：`varchar(100) null`（与 `BangumiFilter` 对齐）
- 存量兼容：已有订阅级规则的订阅回填为 `custom`，保证重构前后行为一致。
  实测：6/6 订阅回填 `custom`，且当时无全局规则 → 对现有用户零可见变化。

## 四、判定收敛到后端

`app/core/filter_utils.py` 只保留一处判定：

```python
select_filter(sub_filter, global_filter, mode) -> FilterRule | None   # 二选一
describe_source(...) -> "global" | "custom" | "none"                  # 供前端展示
filter_episodes(episodes, filter_obj)                                  # 单一规则过滤
```

新增接口 `GET /api/subscriptions/{id}/filtering`：

```json
{
  "filter_mode": "inherit",
  "active_source": "global",
  "global_filter_available": true,
  "active_subtitle_groups": "LoliHouse",
  "matched_episode_ids": [1, 2, 3]
}
```

详情页据此渲染置灰与侧栏「已订阅」标记，**删除前端 `matchEpisode` 与其 `LANGUAGE_KEYWORDS` 副本**。

## 五、前端改动

- `FilterDialog`：新增「规则来源」单选（继承全局 / 自定义）；选择继承时隐藏规则表单并提示
  "全局默认规则已设置/未设置"与"已保存的自定义规则不再生效"；自定义模式保存时校验规则非空；
  删除规则时说明后果（会改为继承）。
- 订阅卡片角标：`自定义过滤` / `全局过滤`（无任何生效规则时不标）。
- 设置页：修正"应用于剧集列表"的不实文案，讲清继承与自定义的关系；全局规则补「语言」字段。
- `constants.ts`：删除已无使用方的 `LANGUAGE_KEYWORDS`。

## 六、验证

- 单测 `tests/test_filter_utils.py`（7 项）：二选一语义、自定义模式不叠加全局、`describe_source`、
  全局规则支持 `language`、无规则放行全部。
- 端到端（测试环境实测）：新建 inherit 订阅 → source=none；无规则切 custom → 400；
  建规则后自动 custom 且命中 15 集；删规则回落 inherit；设置全局规则后 inherit 订阅 source=global
  且 RSS 口径一致；随后清理，订阅数与全局规则恢复原状。
- `/filtering` 的命中集与 RSS feed 条目数交叉核对一致（同一实现，杜绝再次漂移）。

## 七、P3：弹窗合并（已完成）

此前「订阅设置」与「过滤器」是同一份配置的两套界面，字段与能力都不一致：

| | 订阅设置（详情页内联） | 订阅过滤器（`FilterDialog`） |
|---|---|---|
| 可见条件 | 仅**未**订阅 | 仅**已**订阅 |
| 规则来源选择 | ❌ 没有 | ✅ 有 |
| 订阅后再打开 | ❌ 打不开 | ✅ 能开 |

现已合并为 `frontend/src/components/SubscriptionSettingsDialog.vue`，创建与编辑共用：

- `subscriptionId` 有值即编辑模式，为空即新建；新建时「订阅 + 规则」一次提交，
  后端按 `filter_mode` 校验（自定义必须有规则）。
- 编辑模式一次性写入 `{filter_mode, status}`：规则改动走 filter 接口，
  模式与暂停状态走 `PUT /subscriptions/{id}`。
- **订阅状态（暂停/启用）也从 RSS 弹窗移入本弹窗**：RSS 弹窗只负责展示/复制/重新生成链接。
- 入口收敛：详情页未订阅显示「订阅」、已订阅显示「订阅设置」；订阅卡片的「过滤」按钮改为「设置」。
- `FilterDialog.vue` 已删除；顺带修正卡片 tooltip 中"配置**下载**过滤规则"的直推时代遗留措辞。
- 交互细节（按使用反馈调整）：
  - **新建订阅默认选中「自定义规则」**（多数场景是逐个番剧挑字幕组/语言，继承全局属于少数）。
  - **不再有单独的「删除自定义规则」按钮**：既然"空规则 = 不过滤"成立，"清空全部条件并保存"
    就是删除规则（保存时条件为空即删掉规则行），没必要再多一个让人困惑的破坏性按钮。
    表单操作行提供非破坏性的「清空」（与「展开高级选项」同一行，只清表单、保存才落库），
    具体含义放在自定义模式的提示与按钮 tooltip 里，不塞进按钮标签。
  - 取消"自定义规则不能为空"的拦截，允许"自定义 + 无条件"。
  - 表单内的说明文字（暂停说明、规则来源说明）用 `flex-basis: 100%` 独占一行——
    `el-form-item__content` 是 `flex-wrap` 容器，普通 div 默认会和控件挤在同一行。

## 八、未做 / 后续

- **字段级混搭**（全局管一部分字段、订阅覆盖另一部分）：当前是整体覆盖。若确有需求，
  需要为每个字段引入"继承/自定义"标记（且要区分"未设置"与"清空"），复杂度较高。
- **可复用的过滤预设**（方案 4）：未做。
