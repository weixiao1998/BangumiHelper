from app.services.data_sources.mikan import parse_episode_number


def test_parse_episode_number_bracket():
    assert parse_episode_number("[01] 某番剧") == 1
    assert parse_episode_number("[12v3] 某番剧") == 12
    assert parse_episode_number("[24 END] 某番剧") == 24


def test_parse_episode_number_chinese():
    assert parse_episode_number("某番剧 第2话") == 2
    assert parse_episode_number("某番剧 第12集") == 12


def test_parse_episode_number_ep_pattern():
    assert parse_episode_number("某番剧 EP03") == 3
    assert parse_episode_number("某番剧 EP9") == 9


def test_parse_episode_number_season_ep():
    assert parse_episode_number("某番剧 S2E05") == 5


def test_parse_episode_number_no_match():
    assert parse_episode_number("某番剧 无编号标题") == 0


def test_parse_episode_number_fallback_digits():
    # 无明确模式时回退到 2-3 位数字
    assert parse_episode_number("某番剧 128") == 128
