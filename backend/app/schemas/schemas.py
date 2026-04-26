from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str
    invite_code: str | None = None


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
    sub: int | None = None


class EpisodeBase(BaseModel):
    title: str
    episode_number: int = 0
    torrent_url: str | None = None
    magnet_url: str | None = None
    file_size: float | None = None
    subtitle_group: str | None = None
    publish_time: datetime | None = None


class EpisodeResponse(EpisodeBase):
    id: int
    bangumi_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BangumiBase(BaseModel):
    name: str
    keyword: str
    cover: str | None = None
    update_time: str = "Unknown"
    status: int = 0
    data_source: str = "mikan"
    subtitle_groups: str | None = None
    description: str | None = None


class BangumiCreate(BangumiBase):
    pass


class BangumiResponse(BangumiBase):
    id: int
    created_at: datetime
    updated_at: datetime
    episodes: list[EpisodeResponse] = []

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
    downloader_id: int | None = None
    save_path: str | None = None


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    status: int | None = None
    current_episode: int | None = None
    auto_download: bool | None = None
    downloader_id: int | None = None
    save_path: str | None = None


class SubscriptionResponse(SubscriptionBase):
    id: int
    user_id: int
    status: int
    current_episode: int
    rss_token: str | None = None
    created_at: datetime
    updated_at: datetime
    bangumi: BangumiResponse

    class Config:
        from_attributes = True


class BangumiFilterBase(BaseModel):
    bangumi_name: str
    include_keywords: str | None = None
    exclude_keywords: str | None = None
    subtitle_groups: str | None = None
    regex_pattern: str | None = None
    min_episode: int | None = None
    max_episode: int | None = None


class BangumiFilterCreate(BangumiFilterBase):
    pass


class BangumiFilterUpdate(BaseModel):
    include_keywords: str | None = None
    exclude_keywords: str | None = None
    subtitle_groups: str | None = None
    regex_pattern: str | None = None
    min_episode: int | None = None
    max_episode: int | None = None


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
    username: str | None = None
    password: str | None = None
    rpc_url: str | None = None
    token: str | None = None
    is_default: bool = False


class DownloaderConfigCreate(DownloaderConfigBase):
    pass


class DownloaderConfigUpdate(BaseModel):
    name: str | None = None
    downloader_type: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    rpc_url: str | None = None
    token: str | None = None
    is_default: bool | None = None


class DownloaderConfigResponse(DownloaderConfigBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DownloadRequest(BaseModel):
    episode_ids: list[int]
    downloader_id: int | None = None
    download_type: str | None = "magnet"


class DownloadResponse(BaseModel):
    success: bool
    message: str
    download_url: str | None = None


class CalendarResponse(BaseModel):
    weekday: str
    bangumi_list: list[BangumiListResponse]


class SearchResult(BaseModel):
    title: str
    episode_number: int
    torrent_url: str | None = None
    magnet_url: str | None = None
    subtitle_group: str | None = None
    publish_time: datetime | None = None
    file_size: float | None = None


class RSSFeedResponse(BaseModel):
    title: str
    link: str
    description: str
    items: list[SearchResult]


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class InviteCodeCreate(BaseModel):
    max_uses: int = 1
    expires_days: int | None = None


class InviteCodeResponse(BaseModel):
    id: int
    code: str
    created_by: int
    is_used: bool
    max_uses: int
    current_uses: int
    expires_at: datetime | None
    created_at: datetime
    used_at: datetime | None

    class Config:
        from_attributes = True


class RegistrationConfigResponse(BaseModel):
    mode: str
    message: str
