from app.core.security import create_access_token, decode_access_token, get_password_hash, verify_password


def test_password_hash_roundtrip():
    hashed = get_password_hash("s3cret")
    # bcrypt 每次加盐不同，但都能校验通过
    assert verify_password("s3cret", hashed)
    assert not verify_password("wrong", hashed)


def test_token_roundtrip_with_string_subject():
    token = create_access_token("weixiao")
    assert decode_access_token(token) == "weixiao"


def test_token_roundtrip_with_int_subject():
    # create_access_token 会把 subject 转字符串写入 sub
    token = create_access_token(1)
    assert decode_access_token(token) == "1"


def test_decode_invalid_token_returns_none():
    assert decode_access_token("not-a-valid-token") is None
    assert decode_access_token("") is None
