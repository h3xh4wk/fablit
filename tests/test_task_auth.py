"""Deterministic tests for independent task authentication (SPEC-042 §7)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from fablit.platform.task_auth import (
    TaskAuthenticationError,
    bearer_token,
    verify_task_oidc_token,
)

AUDIENCE = "https://fablit.appspot.com/tasks/news-curation"
SERVICE_ACCOUNT = "news-tasks@fablit.iam.gserviceaccount.com"


def verifier(claims: Mapping[str, Any]) -> Any:
    """Build an injectable verifier returning fixed claims."""

    def verify(token: str, audience: str) -> Mapping[str, Any]:
        assert token
        assert audience
        return claims

    return verify


def valid_claims(**overrides: object) -> dict[str, Any]:
    claims: dict[str, Any] = {
        "email": SERVICE_ACCOUNT,
        "email_verified": True,
        "iss": "https://accounts.google.com",
        "aud": AUDIENCE,
    }
    claims.update(overrides)
    return claims


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("Bearer token", "token"),
        ("Bearer   token  ", "token"),
        ("Bearer ", None),
        ("Basic token", None),
        (None, None),
    ],
)
def test_bearer_token_parsing(header: str | None, expected: str | None) -> None:
    assert bearer_token(header) == expected


def test_a_valid_task_token_names_the_task_service_account() -> None:
    principal = verify_task_oidc_token(
        "token",
        audience=AUDIENCE,
        service_account_email=SERVICE_ACCOUNT,
        verifier=verifier(valid_claims()),
    )

    assert principal.email == SERVICE_ACCOUNT


@pytest.mark.parametrize(
    "claims",
    [
        valid_claims(email="someone@example.com"),
        valid_claims(email_verified=False),
        valid_claims(iss="https://issuer.example.com"),
        valid_claims(aud="https://elsewhere.example.com"),
        valid_claims(email=123456),
    ],
)
def test_tokens_for_another_identity_or_audience_are_refused(
    claims: Mapping[str, Any],
) -> None:
    with pytest.raises(TaskAuthenticationError):
        verify_task_oidc_token(
            "token",
            audience=AUDIENCE,
            service_account_email=SERVICE_ACCOUNT,
            verifier=verifier(claims),
        )


def test_a_missing_token_is_refused() -> None:
    with pytest.raises(TaskAuthenticationError, match="identity token"):
        verify_task_oidc_token(
            None,
            audience=AUDIENCE,
            service_account_email=SERVICE_ACCOUNT,
            verifier=verifier(valid_claims()),
        )


@pytest.mark.parametrize(
    ("audience", "service_account"),
    [
        ("", SERVICE_ACCOUNT),
        (" ", SERVICE_ACCOUNT),
        (AUDIENCE, ""),
        (AUDIENCE, "  "),
    ],
)
def test_an_unconfigured_handler_refuses_every_task(
    audience: str, service_account: str
) -> None:
    with pytest.raises(TaskAuthenticationError, match="not configured"):
        verify_task_oidc_token(
            "token",
            audience=audience,
            service_account_email=service_account,
            verifier=verifier(valid_claims()),
        )


def test_a_signature_failure_is_reported_without_the_token() -> None:
    def failing(token: str, audience: str) -> Mapping[str, Any]:
        raise ValueError(f"signature invalid for {token}")

    with pytest.raises(TaskAuthenticationError) as raised:
        verify_task_oidc_token(
            "super-secret-token",
            audience=AUDIENCE,
            service_account_email=SERVICE_ACCOUNT,
            verifier=failing,
        )

    assert "super-secret-token" not in str(raised.value)


def test_case_insensitive_service_account_matching() -> None:
    principal = verify_task_oidc_token(
        "token",
        audience=AUDIENCE,
        service_account_email=SERVICE_ACCOUNT.upper(),
        verifier=verifier(valid_claims()),
    )

    assert principal.email == SERVICE_ACCOUNT
