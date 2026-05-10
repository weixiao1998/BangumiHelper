import re

from app.models.models import BangumiFilter, Episode, GlobalFilter


def _match_episode_with_filter(episode: Episode, filter_obj: BangumiFilter | GlobalFilter | None) -> bool:
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


def match_episode(episode: Episode, filter_obj: BangumiFilter | None) -> bool:
    return _match_episode_with_filter(episode, filter_obj)


def filter_episodes(
    episodes: list[Episode],
    filter_obj: BangumiFilter | None = None,
    global_filter_obj: GlobalFilter | None = None,
) -> list[Episode]:
    return [
        ep
        for ep in episodes
        if _match_episode_with_filter(ep, global_filter_obj) and _match_episode_with_filter(ep, filter_obj)
    ]
