"""Unit tests for platform authoring authentication primitives (SEC-001)."""

from __future__ import annotations

import base64

from starlette.responses import Response

from fablit.platform.authoring_auth import (
    AUTHORING_COOKIE_NAME,
    clear_authoring_cookie,
    extract_authoring_credential,
    extract_authoring_token_from_cookie,
    parse_basic_auth_password,
    set_authoring_cookie,
    verify_authoring_secret,
)


def test_verify_authoring_secret_matches() -> None:
    assert verify_authoring_secret("secret123", "secret123") is True


def test_verify_authoring_secret_mismatch() -> None:
    assert verify_authoring_secret("wrong", "secret123") is False


def test_verify_authoring_secret_none_or_empty() -> None:
    assert verify_authoring_secret(None, "secret123") is False
    assert verify_authoring_secret("", "secret123") is False
    assert verify_authoring_secret("secret123", None) is False
    assert verify_authoring_secret("secret123", "") is False
    assert verify_authoring_secret(None, None) is False
    assert verify_authoring_secret("   ", "secret123") is False
    assert verify_authoring_secret("secret123", "   ") is False


def test_verify_authoring_secret_strips_whitespace() -> None:
    assert verify_authoring_secret("  secret123  ", "secret123") is True
    assert verify_authoring_secret("secret123", "  secret123  ") is True


def test_parse_basic_auth_password() -> None:
    # username:password
    encoded = base64.b64encode(b"author:secret123").decode("utf-8")
    assert parse_basic_auth_password(f"Basic {encoded}") == "secret123"

    # :password
    encoded = base64.b64encode(b":secret123").decode("utf-8")
    assert parse_basic_auth_password(f"Basic {encoded}") == "secret123"

    # password without colon
    encoded = base64.b64encode(b"secret123").decode("utf-8")
    assert parse_basic_auth_password(f"Basic {encoded}") == "secret123"

    # invalid header
    assert parse_basic_auth_password("Bearer abc") is None
    assert parse_basic_auth_password(None) is None
    assert parse_basic_auth_password("Basic invalid_base64!@#") is None


def test_extract_authoring_token_from_cookie() -> None:
    cookie_str = f"other=123; {AUTHORING_COOKIE_NAME}=my-token; anon=abc"
    assert extract_authoring_token_from_cookie(cookie_str) == "my-token"

    assert extract_authoring_token_from_cookie("other=123") is None
    assert extract_authoring_token_from_cookie(None) is None
    assert extract_authoring_token_from_cookie("invalid cookie ;;; format") is None


def test_extract_authoring_credential_precedence() -> None:
    # 1. Bearer header
    assert (
        extract_authoring_credential(
            authorization_header="Bearer bearer-token",
            cookie_header=f"{AUTHORING_COOKIE_NAME}=cookie-token",
            custom_header="header-token",
        )
        == "bearer-token"
    )

    # 2. Basic auth header
    basic_val = f"Basic {base64.b64encode(b':basic-token').decode('utf-8')}"
    assert (
        extract_authoring_credential(
            authorization_header=basic_val,
            cookie_header=f"{AUTHORING_COOKIE_NAME}=cookie-token",
            custom_header="header-token",
        )
        == "basic-token"
    )

    # 3. Custom header
    assert (
        extract_authoring_credential(
            authorization_header=None,
            cookie_header=f"{AUTHORING_COOKIE_NAME}=cookie-token",
            custom_header="custom-token",
        )
        == "custom-token"
    )

    # 4. Cookie
    assert (
        extract_authoring_credential(
            authorization_header=None,
            cookie_header=f"{AUTHORING_COOKIE_NAME}=cookie-token",
            custom_header=None,
        )
        == "cookie-token"
    )

    # None
    assert extract_authoring_credential(None, None, None) is None


def test_set_and_clear_authoring_cookie() -> None:
    response = Response()
    set_authoring_cookie(response, "test-token", secure=True)

    set_cookie_header = response.headers.get("set-cookie")
    assert set_cookie_header is not None
    assert f"{AUTHORING_COOKIE_NAME}=test-token" in set_cookie_header
    assert "Path=/authoring" in set_cookie_header
    assert "HttpOnly" in set_cookie_header
    assert "samesite=lax" in set_cookie_header.lower()
    assert "secure" in set_cookie_header.lower()

    # Clear cookie
    clear_response = Response()
    clear_authoring_cookie(clear_response)
    clear_header = clear_response.headers.get("set-cookie")
    assert clear_header is not None
    assert f"{AUTHORING_COOKIE_NAME}=" in clear_header
    assert "Path=/authoring" in clear_header
