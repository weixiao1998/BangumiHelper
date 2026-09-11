class RegistrationMode:
    OPEN = "open"
    CLOSED = "closed"
    INVITE_ONLY = "invite_only"

    ALL_MODES = [OPEN, CLOSED, INVITE_ONLY]

    @classmethod
    def is_valid(cls, mode: str) -> bool:
        return mode in cls.ALL_MODES


# 订阅语言选项: value 为存储值(逗号分隔), keywords 用于匹配剧集标题
# 前端 LANGUAGE_OPTIONS 需与此保持一致
LANGUAGE_OPTIONS = [
    {"value": "简体中字", "keywords": ["简体", "简中", "简繁", "简日", "中字", "chs"]},
    {"value": "繁体中字", "keywords": ["繁体", "繁中", "繁日", "cts"]},
    {"value": "生肉", "keywords": ["生肉", "raw", "无字幕", "無字幕"]},
    {"value": "双语字幕", "keywords": ["双语", "简繁", "简日", "繁日", "中日"]},
]

LANGUAGE_KEYWORDS = {item["value"]: item["keywords"] for item in LANGUAGE_OPTIONS}


class FilterMode:
    """订阅过滤规则的来源。

    INHERIT: 使用用户的「全局默认规则」；CUSTOM: 使用订阅自身的规则。
    两者互斥、不叠加（此前是硬 AND，用户无法为单个订阅开例外）。
    """

    INHERIT = "inherit"
    CUSTOM = "custom"

    ALL_MODES = [INHERIT, CUSTOM]

    @classmethod
    def is_valid(cls, mode: str) -> bool:
        return mode in cls.ALL_MODES
