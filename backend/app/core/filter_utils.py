"""过滤规则的统一判定。

设计（详见 documents/filter-redesign.md）：一个订阅在任一时刻只有**一份**生效规则：

- `filter_mode = inherit`（默认）→ 使用用户的「全局默认规则」（GlobalFilter）
- `filter_mode = custom`         → 使用订阅自身的规则（BangumiFilter）

两者互斥、不叠加。此前是「全局 AND 订阅」的硬叠加，既无法为单个订阅开例外，
也让"最终会不会下载"难以预测。
"""

import re

from app.core.constants import LANGUAGE_KEYWORDS, FilterMode
from app.models.models import BangumiFilter, Episode, GlobalFilter

FilterRule = BangumiFilter | GlobalFilter


def has_conditions(rule: FilterRule | None) -> bool:
    """规则是否真的设置了条件。

    **空规则等同于"不过滤"**：允许"自定义模式 + 无条件"存在，用来显式表达
    "这个订阅不做过滤"，此时不该显示成"已过滤"。
    """
    if rule is None:
        return False
    return any(
        [
            rule.include_keywords,
            rule.exclude_keywords,
            rule.subtitle_groups,
            rule.language,
            rule.regex_pattern,
            rule.min_episode is not None,
            rule.max_episode is not None,
        ]
    )


def select_filter(
    sub_filter: BangumiFilter | None,
    global_filter: GlobalFilter | None,
    mode: str | None,
) -> FilterRule | None:
    """按订阅的 filter_mode 选出唯一生效的规则；返回 None 表示不过滤。

    所选规则若为空规则，同样返回 None（空规则 = 不过滤）。
    """
    rule = sub_filter if mode == FilterMode.CUSTOM else global_filter
    return rule if has_conditions(rule) else None


def describe_source(
    sub_filter: BangumiFilter | None,
    global_filter: GlobalFilter | None,
    mode: str | None,
) -> str:
    """返回生效规则来源，供前端展示：global / custom / none。"""
    rule = select_filter(sub_filter, global_filter, mode)
    if rule is None:
        return "none"
    return "custom" if mode == FilterMode.CUSTOM else "global"


def _match_episode_with_filter(episode: Episode, filter_obj: FilterRule | None) -> bool:
    if not filter_obj:
        return True

    if filter_obj.include_keywords:
        keywords = [kw.strip() for kw in filter_obj.include_keywords.split(",") if kw.strip()]
        for kw in keywords:
            if kw.lower() not in episode.title.lower():
                return False

    if filter_obj.exclude_keywords:
        keywords = [kw.strip() for kw in filter_obj.exclude_keywords.split(",") if kw.strip()]
        for kw in keywords:
            if kw.lower() in episode.title.lower():
                return False

    if filter_obj.subtitle_groups:
        allowed_groups = [sg.strip() for sg in filter_obj.subtitle_groups.split(",") if sg.strip()]
        if episode.subtitle_group:
            if not any(allowed.lower() in episode.subtitle_group.lower() for allowed in allowed_groups):
                return False
        else:
            if allowed_groups:
                return False

    # BangumiFilter 与 GlobalFilter 字段已对齐（都含 language），直接取属性即可
    if filter_obj.language:
        title = episode.title.lower()
        languages = [lang.strip() for lang in filter_obj.language.split(",") if lang.strip()]
        matched = False
        for lang in languages:
            keywords = [kw.lower() for kw in (LANGUAGE_KEYWORDS.get(lang) or [lang])]
            if any(kw in title for kw in keywords):
                matched = True
                break
        if not matched:
            return False

    if filter_obj.regex_pattern:
        try:
            if not re.search(filter_obj.regex_pattern, episode.title):
                return False
        except re.error:
            pass

    if filter_obj.min_episode is not None and episode.episode_number < filter_obj.min_episode:
        return False

    if filter_obj.max_episode is not None and episode.episode_number > filter_obj.max_episode:
        return False

    return True


def filter_episodes(episodes: list[Episode], filter_obj: FilterRule | None = None) -> list[Episode]:
    """按唯一生效规则过滤剧集；filter_obj 为 None 时全部保留。"""
    return [ep for ep in episodes if _match_episode_with_filter(ep, filter_obj)]
