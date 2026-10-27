"""Independent authentication for durable task requests (SPEC-042 §7).

Task execution must not be authorised by an author's browser session, and it
must not trust a caller-controlled header as proof of origin. A Cloud Tasks
push request carries a Google-signed OIDC identity token issued to the task
service account; this module verifies that token against the expected audience
and service account before the protected handler runs.

Verification is injectable so tests can exercise acceptance and refusal
without network access or cloud credentials.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Final

logger = logging.getLogger("fablit.tasks.auth")

#: Google identity tokens are issued by one of these issuers.
_ALLOWED_ISSUERS: Final[frozenset[str]] = frozenset(
    {"accounts.google.com", "https://accounts.google.com"}
)

#: Signature: ``(token, audience) -> verified claims``.
OidcVerifier = Callable[[str, str], Mapping[str, Any]]


class TaskAuthenticationError(Exception):
    """Raised when a task request cannot be authenticated (SPEC-042 §7).

    The message is safe to log and return: it names the reason without
    echoing the token or any claim value.
    """


@dataclass(frozen=True)
class TaskPrincipal:
    """The verified identity that dispatched one task."""

    email: str


def bearer_token(header_value: str | None) -> str | None:
    """Extract a bearer token from an Authorization header, if present."""
    if not header_value:
        return None
    prefix = "Bearer "
    if not header_value.startswith(prefix):
        return None
    token = header_value[len(prefix) :].strip()
    return token or None


def verify_task_oidc_token(
    token: str | None,
    *,
    audience: str,
    service_account_email: str,
    verifier: OidcVerifier | None = None,
) -> TaskPrincipal:
    """Verify a Google-issued OIDC token for the task handler.

    Raises:
        TaskAuthenticationError: When the request carries no token, the token
            cannot be verified, or it was not issued for this handler and
            service account.
    """
    if not isinstance(audience, str) or not audience.strip():
        raise TaskAuthenticationError("the task handler audience is not configured")
    if not isinstance(service_account_email, str) or (
        not service_account_email.strip()
    ):
        raise TaskAuthenticationError("the task service account is not configured")
    if token is None:
        raise TaskAuthenticationError("a task request requires an identity token")

    verify = verifier or _google_oidc_verifier
    try:
        claims = verify(token, audience.strip())
    except TaskAuthenticationError:
        raise
    except Exception:
        logger.warning("task identity token was rejected")
        raise TaskAuthenticationError("the task identity token is not valid") from None

    email = claims.get("email")
    if not isinstance(email, str) or email.casefold() != (
        service_account_email.strip().casefold()
    ):
        raise TaskAuthenticationError(
            "the task identity is not the task service account"
        )
    if claims.get("email_verified") is not True:
        raise TaskAuthenticationError("the task identity email is not verified")
    issuer = claims.get("iss")
    if issuer not in _ALLOWED_ISSUERS:
        raise TaskAuthenticationError("the task identity token has an unknown issuer")
    if claims.get("aud") != audience.strip():
        raise TaskAuthenticationError("the task identity token has the wrong audience")
    return TaskPrincipal(email=email)


def _google_oidc_verifier(token: str, audience: str) -> Mapping[str, Any]:
    """Verify a Google OIDC token with the official library."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token
    except ImportError as exc:  # pragma: no cover - production dependency
        raise TaskAuthenticationError(
            "google-auth is required to verify task identity tokens"
        ) from exc

    claims: dict[str, Any] = id_token.verify_oauth2_token(
        token,
        Request(),
        audience=audience,
    )
    return claims
