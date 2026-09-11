"""RSS feed 构造与窗口控制。

本项目对「自动下载」的投放方式是 RSS：服务器出 feed，用户自己的下载器（qBittorrent /
Transmission 等）按固定间隔拉取。这样用户下载器即便位于 NAT 之后也能工作（由客户端出站）。

窗口控制很关键：单番剧剧集数最多可达数百集、用户级 feed 是全部订阅之和。若不做窗口，
用户第一次把链接加进下载器就会把历史全集灌进去，也会让每次轮询都全量查库。
默认取「最近 N 天」与「最近 M 条」中先到者，可用查询参数覆盖，`0` 表示不限。

**注意 days 与 limit 的作用点不同**（这是踩过的坑）：
过滤条件（字幕组/关键词/语言等）只能在 Python 里判定，所以
- `days` 在 SQL 层截取时间窗口，同时把查询代价限定住；
- `limit` 必须在**过滤之后**再截断。若把 LIMIT 下推到 SQL，最新的若干集可能全是
  不匹配过滤条件的内容，它们会吃掉整个窗口，导致 feed 明明有命中却返回空
  （实测：某订阅 60 天窗口内有 8 集命中，但 limit=3 时因最新 3 集字幕组不匹配而返回 0 条）。
"""

from datetime import UTC, datetime, timedelta

from feedgenerator import Enclosure, Rss201rev2Feed
from sqlalchemy import Select

from app.core.utils import utc_now
from app.models.models import Episode

# 默认窗口：最近 60 天 或 最近 100 条，取先到者
DEFAULT_WINDOW_DAYS = 60
DEFAULT_WINDOW_LIMIT = 100


def resolve_window(days: int | None = None, limit: int | None = None) -> tuple[int | None, int | None]:
    """把查询参数归一化为 (days, limit)：None 取默认值，0 表示不限。"""
    if days is None:
        days = DEFAULT_WINDOW_DAYS
    if limit is None:
        limit = DEFAULT_WINDOW_LIMIT
    return (days if days > 0 else None, limit if limit > 0 else None)


def apply_window(stmt: Select, days: int | None, *, now: datetime | None = None) -> Select:
    """给剧集查询加上时间窗口并按发布时间倒序（最新的在前）。

    刻意不在这里下推 LIMIT：条数上限必须在过滤之后应用，详见模块头部说明。
    """
    if days is not None:
        cutoff = (now or utc_now()) - timedelta(days=days)
        # publish_time 为空的历史数据无法判断新旧，按窗口排除
        stmt = stmt.where(Episode.publish_time.is_not(None), Episode.publish_time >= cutoff)
    return stmt.order_by(Episode.publish_time.desc(), Episode.id.desc())


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def build_feed(
    *,
    title: str,
    link: str,
    description: str,
    entries: list[tuple[str | None, Episode]],
) -> str:
    """构造 RSS 2.0 feed。

    entries 为 (标题前缀, 剧集) 列表：单订阅 feed 前缀为 None（只用剧集标题），
    用户级聚合 feed 前缀为番剧名，便于在同一个 feed 里区分来源。
    """
    feed = Rss201rev2Feed(title=title, link=link, description=description)

    for prefix, ep in entries:
        description_parts = [f"第 {ep.episode_number} 集"]
        if ep.subtitle_group:
            description_parts.append(f"字幕组: {ep.subtitle_group}")
        if ep.file_size:
            size_mb = ep.file_size / (1024 * 1024)
            description_parts.append(f"大小: {size_mb:.2f} MB")

        # enclosure 必须用种子文件：qBittorrent 等客户端的 RSS 自动下载依赖它。
        # 注意 feedgenerator 的参数名是 enclosures（复数，且要求 Enclosure 实例）——
        # 传单数 enclosure= 会被 **kwargs 静默吞掉，feed 里不会出现 <enclosure>
        # （历史 bug：此前 RSS 一直没有 enclosure）。
        enclosures = []
        if ep.torrent_url:
            enclosures.append(
                Enclosure(
                    ep.torrent_url,
                    # Enclosure 的三个参数都会被直接写进 XML 属性，必须是字符串
                    str(int(ep.file_size) if ep.file_size else 0),
                    "application/x-bittorrent",
                )
            )

        feed.add_item(
            title=f"[{prefix}] {ep.title}" if prefix else ep.title,
            link=ep.magnet_url or ep.torrent_url or "",
            description="；".join(description_parts),
            # 稳定且唯一，客户端据此去重，避免同一集重复下载
            unique_id=f"episode-{ep.id}",
            pubdate=_as_utc(ep.publish_time),
            enclosures=enclosures,
        )

    # feedgenerator 无类型标注，writeString 返回 Any，这里显式收敛为 str
    return str(feed.writeString("utf-8"))
