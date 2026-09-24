"""Anonymous learner identity primitives (SPEC-024).

SPEC-024 §5: each anonymous learner receives a unique, opaque Fablit learner
identity — high-entropy, collision-resistant, encoding no personal
information, and not derived from any identifying data. The identity is
persisted as a secure browser cookie (§5.2) so practice history remains
private to that learner's browser, and the internal ``learner_id`` stays the
stable ownership key for practice history (§3.3).

The primitives here are deliberately tiny: identity *generation* and identity
*cookie transport*. Where they are applied to requests (resolution,
per-learner application wiring) lives at the web/application boundary
(``app.learner_session``), keeping this module independent of FastAPI.
"""

from __future__ import annotations

from http.cookies import SimpleCookie
from typing import Final, Literal
from uuid import UUID, uuid4

from starlette.responses import Response

#: Cookie carrying the anonymous learner identity (SPEC-024 §5.2). The name
#: deliberately avoids the word "user" — the cookie identifies an anonymous
#: learner's browser, not an account.
LEARNER_ID_COOKIE_NAME: Final[str] = "fablit_learner_id"

#: Cookie lifetime: one year. The anonymous browser identity is intentionally
#: long-lived but not permanent; a cleared cookie simply starts a fresh
#: anonymous learner (§5.3).
LEARNER_ID_COOKIE_MAX_AGE_SECONDS: Final[int] = 365 * 24 * 60 * 60

#: Cookie attributes (§5.2): not readable by client-side JavaScript, never
#: forwarded on cross-site requests, and (in production) only sent over
#: secure connections.
LEARNER_ID_COOKIE_HTTPONLY: Final[bool] = True
LEARNER_ID_COOKIE_SECURE: Final[bool] = True
LEARNER_ID_COOKIE_SAMESITE: Final[Literal["lax", "strict", "none"]] = "lax"


def generate_learner_id() -> UUID:
    """Generate a new opaque, high-entropy anonymous learner identity (§5.1).

    The identifier is a random UUID: unique with practical collision
    resistance, encoding no personal information, and not derived from
    email, name, IP address, device fingerprint, or any other identifying
    data.
    """
    return uuid4()


def read_learner_id_from_cookie(cookie_header: str | None) -> UUID | None:
    """Extract the learner identity from a raw ``Cookie`` header, if present.

    Returns ``None`` when the header is absent, the named cookie is not set,
    or the value is not a valid identity; the caller then treats the request
    as a new anonymous learner (§5.2). Parsing uses the standard library
    cookie parser so quoting and escaping follow browser conventions, and a
    malformed header never breaks identity resolution.
    """
    if not cookie_header:
        return None
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except Exception:
        return None
    morsel = cookie.get(LEARNER_ID_COOKIE_NAME)
    if morsel is None:
        return None
    try:
        return UUID(morsel.value)
    except ValueError:
        return None


def set_learner_cookie(
    response: Response,
    learner_id: UUID,
    *,
    secure: bool = LEARNER_ID_COOKIE_SECURE,
) -> None:
    """Attach the learner identity cookie to a response (§5.2).

    ``secure`` defaults to ``True`` so the identity cookie is only ever sent
    over HTTPS in production. The one deployment shape where plain HTTP is
    legitimate — test clients and local development — passes
    ``secure=False``; the environment drives that choice, not the caller.
    """
    response.set_cookie(
        LEARNER_ID_COOKIE_NAME,
        str(learner_id),
        max_age=LEARNER_ID_COOKIE_MAX_AGE_SECONDS,
        path="/",
        httponly=LEARNER_ID_COOKIE_HTTPONLY,
        samesite=LEARNER_ID_COOKIE_SAMESITE,
        secure=secure,
    )
