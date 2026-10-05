"""Web and security tests for internal AI authoring access protection (SEC-001).

SPEC-032 introduces an internal AI-assisted practice authoring workflow.
SEC-001 establishes the security boundary:
- Unauthenticated requests cannot access authoring UI or AI-generation endpoints.
- Server-side authorization checks occur BEFORE any AI provider invocation.
- AI provider credentials and authoring secrets are never exposed to learners
  or in client-facing responses.
- Public learner routes remain anonymous and completely unaffected.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import create_app
from fablit.config import AppConfig, load_config
from fablit.platform.authoring_auth import AUTHORING_COOKIE_NAME

SECRET = "test-internal-authoring-secret-42"
AI_KEY = "test-ai-provider-api-key-999"


def _configured_client(
    *,
    secret: str | None = SECRET,
    ai_key: str | None = AI_KEY,
    environment: str = "production",
) -> tuple[TestClient, MagicMock]:
    """Build a TestClient with configured authoring secret and a spy AI provider."""
    config: AppConfig = load_config(
        overrides={
            "environment": environment,
            "authoring_secret": secret,
            "ai_provider_api_key": ai_key,
        }
    )
    app = create_app(config)
    spy_provider = MagicMock()
    spy_provider.generate_candidate.return_value = {
        "status": "candidate",
        "id": "candidate-xyz",
        "activity": {
            "title": "Generated Test Practice",
            "instructions": "Follow these steps.",
        },
    }
    app.state.authoring_ai_provider = spy_provider
    return (
        TestClient(app, base_url="https://testserver", raise_server_exceptions=False),
        spy_provider,
    )


# --- Unauthenticated & Unauthorized Rejection (SEC-001 AC-1, AC-2, AC-3) ---


def test_unauthenticated_request_to_authoring_ui_is_rejected() -> None:
    client, _ = _configured_client()
    response = client.get("/authoring")
    assert response.status_code == 401
    assert "Internal Authoring Access" in response.text
    assert "Authoring Secret" in response.text


def test_unauthenticated_direct_request_to_generate_is_rejected() -> None:
    client, _ = _configured_client()
    response = client.post(
        "/authoring/generate",
        json={"practice_area": "Visual Analysis"},
    )
    assert response.status_code == 401
    assert response.json()["error"] == "Unauthorized"


def test_unauthenticated_request_to_candidates_is_rejected() -> None:
    client, _ = _configured_client()
    response = client.get("/authoring/candidates")
    assert response.status_code == 401

    approve_resp = client.post("/authoring/candidates/cand-1/approve")
    assert approve_resp.status_code == 401

    reject_resp = client.post("/authoring/candidates/cand-1/reject")
    assert reject_resp.status_code == 401


def test_invalid_credentials_are_rejected() -> None:
    client, _ = _configured_client()

    # Wrong bearer token
    res1 = client.get(
        "/authoring",
        headers={"Authorization": "Bearer wrong-secret"},
    )
    assert res1.status_code == 401

    # Wrong custom header
    res2 = client.post(
        "/authoring/generate",
        headers={"X-Author-Key": "wrong-secret"},
        json={"practice_area": "Test"},
    )
    assert res2.status_code == 401

    # Wrong cookie
    client.cookies.set(AUTHORING_COOKIE_NAME, "wrong-cookie-secret")
    res3 = client.get("/authoring")
    assert res3.status_code == 401


def test_unauthorized_request_cannot_trigger_ai_provider_call() -> None:
    """Critical SEC-001 requirement: unauthorized requests never call AI provider."""
    client, spy_provider = _configured_client()

    # 1. No credentials
    client.post("/authoring/generate", json={"practice_area": "Visual Analysis"})
    assert spy_provider.generate_candidate.called is False

    # 2. Invalid credentials
    client.post(
        "/authoring/generate",
        headers={"Authorization": "Bearer invalid-token"},
        json={"practice_area": "Visual Analysis"},
    )
    assert spy_provider.generate_candidate.called is False

    # 3. Invalid cookie
    client.cookies.set(AUTHORING_COOKIE_NAME, "bad-cookie")
    client.post("/authoring/generate", json={"practice_area": "Visual Analysis"})
    assert spy_provider.generate_candidate.called is False


# --- Authorized Access (SEC-001 AC-4) ---


def test_authorized_access_via_bearer_token() -> None:
    client, spy_provider = _configured_client()

    headers = {"Authorization": f"Bearer {SECRET}"}
    response = client.get("/authoring", headers=headers)
    assert response.status_code == 200
    assert "Internal Authoring Workspace" in response.text

    generate_resp = client.post(
        "/authoring/generate",
        headers=headers,
        json={
            "practice_area": "Observation Drill",
            "learning_focus": "Focus on details.",
        },
    )
    assert generate_resp.status_code == 200
    assert spy_provider.generate_candidate.called is True
    assert generate_resp.json()["status"] == "candidate"


def test_authorized_access_via_custom_header() -> None:
    client, _ = _configured_client()

    headers = {"X-Author-Key": SECRET}
    response = client.get("/authoring", headers=headers)
    assert response.status_code == 200
    assert "Internal Authoring Workspace" in response.text


def test_authorized_access_via_cookie() -> None:
    client, _ = _configured_client()

    client.cookies.set(AUTHORING_COOKIE_NAME, SECRET)
    response = client.get("/authoring")
    assert response.status_code == 200
    assert "Internal Authoring Workspace" in response.text


def test_candidate_review_endpoints_when_authorized() -> None:
    client, _ = _configured_client()
    headers = {"Authorization": f"Bearer {SECRET}"}

    list_resp = client.get("/authoring/candidates", headers=headers)
    assert list_resp.status_code == 200

    app_resp = client.post("/authoring/candidates/c1/approve", headers=headers)
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "approved"

    rej_resp = client.post("/authoring/candidates/c1/reject", headers=headers)
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "rejected"


# --- Browser Login & Logout Lifecycle ---


def test_login_page_renders_cleanly() -> None:
    client, _ = _configured_client()
    response = client.get("/authoring/login")
    assert response.status_code == 200
    assert "Internal Authoring Access" in response.text
    assert 'name="secret"' in response.text


def test_login_post_invalid_secret_returns_401() -> None:
    client, _ = _configured_client()
    response = client.post("/authoring/login", data={"secret": "wrong-secret"})
    assert response.status_code == 401
    assert "Invalid authoring secret" in response.text


def test_login_post_valid_secret_redirects_and_sets_cookie() -> None:
    client, _ = _configured_client()
    response = client.post(
        "/authoring/login",
        data={"secret": SECRET},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/authoring"
    cookie = response.cookies.get(AUTHORING_COOKIE_NAME)
    assert cookie == SECRET

    # Following redirects with that client now accesses /authoring
    workspace_resp = client.get("/authoring")
    assert workspace_resp.status_code == 200
    assert "Internal Authoring Workspace" in workspace_resp.text


def test_logout_clears_cookie_and_redirects() -> None:
    client, _ = _configured_client()
    login_resp = client.post(
        "/authoring/login",
        data={"secret": SECRET},
        follow_redirects=False,
    )
    assert login_resp.status_code == 303
    assert client.get("/authoring").status_code == 200

    response = client.post("/authoring/logout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    # Subsequent access is now rejected
    unauth_resp = client.get("/authoring")
    assert unauth_resp.status_code == 401


# --- Secure by Default: Unset Secret ---


def test_authoring_disabled_by_default_when_secret_unset() -> None:
    """When secret is unset, authoring is disabled and rejects all access."""
    client, _ = _configured_client(secret=None)

    # Even with an arbitrary token, access is rejected
    res1 = client.get("/authoring", headers={"Authorization": "Bearer any-token"})
    assert res1.status_code == 401

    res2 = client.post("/authoring/login", data={"secret": "any-token"})
    assert res2.status_code == 401


# --- Learner Routes Remain Public & Unaffected (SEC-001 AC-5) ---


def test_public_learner_routes_remain_accessible_without_auth() -> None:
    """Public learner routes require no authoring token or auth prompts."""
    client, _ = _configured_client()

    routes = [
        "/",
        "/practice",
        "/practice/short-drill",
        "/history",
        "/health",
    ]
    for path in routes:
        response = client.get(path)
        assert response.status_code == 200, (
            f"Route {path} should be publicly accessible"
        )
        # Confirm no authoring login prompt appears on learner routes
        assert "Internal Authoring Access" not in response.text
        assert "Authoring Secret" not in response.text


# --- Credential Secrecy: No Leaks to Client (SEC-001 AC-6) ---


def test_provider_credentials_and_secrets_never_leak() -> None:
    """AI provider keys and authoring secrets must NEVER be present in responses."""
    client, _ = _configured_client()

    pages_to_check: list[tuple[str, dict[str, str]]] = [
        ("/", {}),
        ("/history", {}),
        ("/practice", {}),
        ("/authoring/login", {}),
        ("/authoring", {"Authorization": f"Bearer {SECRET}"}),
    ]

    for path, headers in pages_to_check:
        resp = client.get(path, headers=headers)
        # Check that the secret and AI key never appear in HTML
        assert SECRET not in resp.text, f"Secret leaked in {path}"
        assert AI_KEY not in resp.text, f"AI key leaked in {path}"

    # Also check JSON generation response
    gen_resp = client.post(
        "/authoring/generate",
        headers={"Authorization": f"Bearer {SECRET}"},
        json={"practice_area": "Test Area"},
    )
    assert AI_KEY not in gen_resp.text
    assert SECRET not in gen_resp.text


def test_login_page_redirects_if_already_authenticated() -> None:
    client, _ = _configured_client()
    client.cookies.set(AUTHORING_COOKIE_NAME, SECRET)
    response = client.get("/authoring/login", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/authoring"


def test_unauthenticated_request_with_trailing_slash_rejected() -> None:
    client, _ = _configured_client()
    response = client.get("/authoring/")
    assert response.status_code == 401
    assert "Internal Authoring Access" in response.text


def test_ai_provider_failure_returns_502_without_leaks() -> None:
    client, spy_provider = _configured_client()
    spy_provider.generate_candidate.side_effect = RuntimeError(
        "Sensitive internal connection failed: api-key-leak-attempt"
    )

    headers = {"Authorization": f"Bearer {SECRET}"}
    response = client.post(
        "/authoring/generate",
        headers=headers,
        json={"practice_area": "Creative Exercise"},
    )
    assert response.status_code == 502
    assert response.json()["error"] == "Error"
    assert (
        response.json()["detail"]
        == "The AI generation service is temporarily unavailable."
    )
    assert "api-key-leak-attempt" not in response.text
    assert "RuntimeError" not in response.text


def test_candidate_approval_and_rejection_browser_html_flow() -> None:
    client, _ = _configured_client()
    client.cookies.set(AUTHORING_COOKIE_NAME, SECRET)

    headers = {"Accept": "text/html"}
    app_resp = client.post(
        "/authoring/candidates/cand-123/approve",
        headers=headers,
    )
    assert app_resp.status_code == 200
    assert "Candidate cand-123 approved for curated library." in app_resp.text

    rej_resp = client.post(
        "/authoring/candidates/cand-123/reject",
        headers=headers,
    )
    assert rej_resp.status_code == 200
    assert "Candidate cand-123 rejected." in rej_resp.text


def test_login_post_in_production_sets_secure_cookie() -> None:
    client, _ = _configured_client(environment="production")
    response = client.post(
        "/authoring/login",
        data={"secret": SECRET},
        follow_redirects=False,
    )
    assert response.status_code == 303
    cookie_header = response.headers.get("set-cookie", "").lower()
    assert "secure" in cookie_header
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    assert "path=/authoring" in cookie_header
