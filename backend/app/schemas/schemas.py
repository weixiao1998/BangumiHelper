from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str
    invite_code: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[int] = None


class EpisodeBase(BaseModel):
    title: str
    episode_number: int = 0
    torrent_url: Optional[str] = None
    magnet_url: Optional[str] = None
    file_size: Optional[float] = None
    subtitle_group: Optional[str] = None
    publish_time: Optional[datetime] = None


class EpisodeResponse(EpisodeBase):
    id: int
    bangumi_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BangumiBase(BaseModel):
    name: str
    keyword: str
    cover: Optional[str] = None
    update_time: str = "Unknown"
    status: int = 0
    data_source: str = "mikan"
    subtitle_groups: Optional[str] = None
    description: Optional[str] = None


class BangumiCreate(BangumiBase):
    pass


class BangumiResponse(BangumiBase):
    id: int
    created_at: datetime
    updated_at: datetime
    episodes: List[EpisodeResponse] = []

    class Config:
        from_attributes = True


class BangumiListResponse(BangumiBase):
    id: int
    is_subscribed: bool = False
    current_episode: int = 0

    class Config:
        from_attributes = True


class SubscriptionBase(BaseModel):
    bangumi_id: int
    auto_download: bool = False
    downloader_id: Optional[int] = None
    save_path: Optional[str] = None


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    status: Optional[int] = None
    current_episode: Optional[int] = None
    auto_download: Optional[bool] = None
    downloader_id: Optional[int] = None
    save_path: Optional[str] = None


class SubscriptionResponse(SubscriptionBase):
    id: int
    user_id: int
    status: int
    current_episode: int
    rss_token: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    bangumi: BangumiResponse

    class Config:
        from_attributes = True


class BangumiFilterBase(BaseModel):
    bangumi_name: str
    include_keywords: Optional[str] = None
    exclude_keywords: Optional[str] = None
    subtitle_groups: Optional[str] = None
    regex_pattern: Optional[str] = None
    min_episode: Optional[int] = None
    max_episode: Optional[int] = None


class BangumiFilterCreate(BangumiFilterBase):
    pass


class BangumiFilterUpdate(BaseModel):
    include_keywords: Optional[str] = None
    exclude_keywords: Optional[str] = None
    subtitle_groups: Optional[str] = None
    regex_pattern: Optional[str] = None
    min_episode: Optional[int] = None
    max_episode: Optional[int] = None


class BangumiFilterResponse(BangumiFilterBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DownloaderConfigBase(BaseModel):
    name: str
    downloader_type: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    rpc_url: Optional[str] = None
    token: Optional[str] = None
    is_default: bool = False


class DownloaderConfigCreate(DownloaderConfigBase):
    pass


class DownloaderConfigUpdate(BaseModel):
    name: Optional[str] = None
    downloader_type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    rpc_url: Optional[str] = None
    token: Optional[str] = None
    is_default: Optional[bool] = None


class DownloaderConfigResponse(DownloaderConfigBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DownloadRequest(BaseModel):
    episode_ids: List[int]
    downloader_id: Optional[int] = None
    download_type: Optional[str] = "magnet"


class DownloadResponse(BaseModel):
    success: bool
    message: str
    download_url: Optional[str] = None


class CalendarResponse(BaseModel):
    weekday: str
    bangumi_list: List[BangumiListResponse]


class SearchResult(BaseModel):
    title: str
    episode_number: int
    torrent_url: Optional[str] = None
    magnet_url: Optional[str] = None
    subtitle_group: Optional[str] = None
    publish_time: Optional[datetime] = None
    file_size: Optional[float] = None


class RSSFeedResponse(BaseModel):
    title: str
    link: str
    description: str
    items: List[SearchResult]


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class InviteCodeCreate(BaseModel):
    max_uses: int = 1
    expires_days: Optional[int] = None


class InviteCodeResponse(BaseModel):
    id: int
    code: str
    created_by: int
    is_used: bool
    max_uses: int
    current_uses: int
    expires_at: Optional[datetime]
    created_at: datetime
    used_at: Optional[datetime]

    class Config:
        from_attributes = True


class RegistrationConfigResponse(BaseModel):
    mode: str
    message: str
