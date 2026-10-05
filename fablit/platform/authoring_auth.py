"""Internal AI authoring access and authentication primitives (SEC-001).

SPEC-032 introduces an internal AI-assisted practice authoring workflow.
SEC-001 establishes the security boundary before SPEC-032 is implemented:
the authoring interface and AI-generation endpoints are strictly internal,
protected server-side by a shared authoring secret, while public learner-facing
routes remain open and anonymous without requiring learner accounts.

This module provides the core authentication primitives:
- Constant-time secret comparison preventing timing attacks.
- Extraction of authoring credentials from Authorization headers, custom headers,
  or secure session cookies.
- Cookie management for browser-based authoring sessions.
"""

from __future__ import annotations

import base64
import hmac
from http.cookies import SimpleCookie
from typing import Final, Literal

from starlette.responses import Response

#: Cookie carrying the authoring session token (SEC-001).
AUTHORING_COOKIE_NAME: Final[str] = "fablit_author_token"

#: Cookie lifetime: 7 days.
AUTHORING_COOKIE_MAX_AGE_SECONDS: Final[int] = 7 * 24 * 60 * 60

#: Cookie attributes: HttpOnly, restricted to the /authoring path, SameSite=Lax.
AUTHORING_COOKIE_HTTPONLY: Final[bool] = True
AUTHORING_COOKIE_PATH: Final[str] = "/authoring"
AUTHORING_COOKIE_SAMESITE: Final[Literal["lax", "strict", "none"]] = "lax"


def verify_authoring_secret(
    provided: str | None,
    configured_secret: str | None,
) -> bool:
    """Verify the provided secret against the configured authoring secret.

    Uses constant-time comparison to prevent timing attacks.
    Returns False if either secret is empty, None, or if configured_secret
    is unset (secure by default: authoring is disabled when unset).
    """
    if not configured_secret or not configured_secret.strip():
        return False
    if not provided or not provided.strip():
        return False
    return hmac.compare_digest(
        provided.strip().encode("utf-8"),
        configured_secret.strip().encode("utf-8"),
    )


def parse_basic_auth_password(header_value: str | None) -> str | None:
    """Extract the password/secret from an HTTP Basic Authorization header."""
    if not header_value:
        return None
    prefix = "Basic "
    if not header_value.startswith(prefix):
        return None
    encoded = header_value[len(prefix) :].strip()
    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
    except Exception:
        return None
    # Format is username:password or :password
    if ":" in decoded:
        _, password = decoded.split(":", 1)
        return password or None
    return decoded or None


def extract_authoring_token_from_cookie(cookie_header: str | None) -> str | None:
    """Extract the authoring token from the Cookie header, if present."""
    if not cookie_header:
        return None
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except Exception:
        return None
    morsel = cookie.get(AUTHORING_COOKIE_NAME)
    if morsel is None:
        return None
    token = morsel.value.strip()
    return token if token else None


def extract_authoring_credential(
    authorization_header: str | None,
    cookie_header: str | None,
    custom_header: str | None = None,
) -> str | None:
    """Extract the authoring credential from header, cookie, or custom header.

    Precedence:
    1. Bearer token in Authorization header
    2. Basic Auth password in Authorization header
    3. X-Author-Key / custom header
    4. fablit_author_token cookie
    """
    if authorization_header:
        if authorization_header.startswith("Bearer "):
            token = authorization_header[len("Bearer ") :].strip()
            if token:
                return token
        basic = parse_basic_auth_password(authorization_header)
        if basic:
            return basic

    if custom_header and custom_header.strip():
        return custom_header.strip()

    if cookie_header:
        cookie_token = extract_authoring_token_from_cookie(cookie_header)
        if cookie_token:
            return cookie_token

    return None


def set_authoring_cookie(
    response: Response,
    token: str,
    *,
    secure: bool = True,
) -> None:
    """Attach the authoring session cookie to a response.

    Scoped strictly to the /authoring path so it is never sent on public
    learner routes.
    """
    response.set_cookie(
        AUTHORING_COOKIE_NAME,
        token,
        max_age=AUTHORING_COOKIE_MAX_AGE_SECONDS,
        path=AUTHORING_COOKIE_PATH,
        httponly=AUTHORING_COOKIE_HTTPONLY,
        samesite=AUTHORING_COOKIE_SAMESITE,
        secure=secure,
    )


def clear_authoring_cookie(response: Response) -> None:
    """Clear the authoring session cookie."""
    response.delete_cookie(
        AUTHORING_COOKIE_NAME,
        path=AUTHORING_COOKIE_PATH,
    )
    response.delete_cookie(
        AUTHORING_COOKIE_NAME,
        path="/",
    )
