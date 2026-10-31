"""Web tests for shared candidate state across instances (SPEC-032 / FIX-7)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.main import create_app
from fablit.config import load_config
from fablit.platform.datastore_authoring_store import DatastoreAuthoringCandidateStore
from tests.persistence.test_datastore_authoring_store import (
    FakeDatastoreClient,
    _make_candidate,
)

SECRET = "shared-authoring-secret"
HEADERS = {"Authorization": f"Bearer {SECRET}"}
BRIEF = {
    "practice_area": "Visual analysis",
    "learner_context": "A learner practising close observation.",
    "purpose": "Distinguish visible evidence from interpretation.",
    "intended_mode": "short-drill",
    "response_form": "A short written observation.",
    "evaluation_intent": "Look for specific observable details.",
    "feedback_intent": "Identify useful evidence and one next step.",
    "reflection_intent": "Notice which observation strategy was useful.",
}


def _create_paired_clients(
    retention_days: int = 30,
) -> tuple[TestClient, TestClient, FakeDatastoreClient]:
    shared_client = FakeDatastoreClient()

    def make_instance() -> TestClient:
        config = load_config(
            overrides={
                "environment": "testing",
                "authoring_secret": SECRET,
                "authoring_candidate_store": "memory",
                "authoring_candidate_retention_days": retention_days,
            }
        )
        app = create_app(config)
        # Wire Datastore store backed by the shared client
        app.state.authoring_candidate_store = DatastoreAuthoringCandidateStore(
            client=shared_client, retention_days=retention_days
        )
        provider = Mock()
        provider.generate.return_value = SimpleNamespace(
            candidate_data={
                "title": "Evidence-based observation",
                "description": "Describe one visible element.",
                "contract": {
                    "purpose": "Distinguish visible evidence from interpretation.",
                    "task": "Identify three visible facts in the painting.",
                    "expected_thinking": (
                        "Focus purely on descriptive observations without"
                        " interpretation."
                    ),
                    "response_contract": "Three concise factual statements.",
                    "evaluation_intent": "Check for observable evidence.",
                    "feedback_intent": (
                        "Specific constructive feedback on observation accuracy."
                    ),
                    "reflection_intent": (
                        "Reflect on separating fact from interpretation."
                    ),
                    "continuation_intent": "Advance to comparative visual analysis.",
                },
            },
            provider="test-gemini",
            model="gemini-2.5-flash",
            generated_at=datetime.now(UTC),
        )
        app.state.authoring_ai_provider = provider
        return TestClient(app)

    return make_instance(), make_instance(), shared_client


def test_cross_instance_authoring_workflow() -> None:
    client_a, client_b, _ = _create_paired_clients()

    # Instance A: Generate candidate
    response_gen = client_a.post(
        "/authoring/generate",
        headers={**HEADERS, "Accept": "application/json"},
        json=BRIEF,
    )
    assert response_gen.status_code == 200
    candidate_id = response_gen.json()["id"]

    # Instance B: Fetch candidate detail
    response_b = client_b.get(
        f"/authoring/candidates/{candidate_id}",
        headers={**HEADERS, "Accept": "application/json"},
    )
    assert response_b.status_code == 200
    candidate_data = response_b.json()
    assert candidate_data["id"] == candidate_id
    assert candidate_data["title"] == "Evidence-based observation"
    assert candidate_data["revision"] == 1
    assert candidate_data["status"] == "candidate"

    # Instance A: Edit candidate
    response_edit = client_a.post(
        f"/authoring/candidates/{candidate_id}/edit",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"title": "Refined Observation Drill"},
    )
    assert response_edit.status_code == 200
    assert response_edit.json()["revision"] == 2
    assert response_edit.json()["title"] == "Refined Observation Drill"

    # Instance B: Read updated candidate
    response_b_after_edit = client_b.get(
        f"/authoring/candidates/{candidate_id}",
        headers={**HEADERS, "Accept": "application/json"},
    )
    assert response_b_after_edit.status_code == 200
    assert response_b_after_edit.json()["revision"] == 2
    assert response_b_after_edit.json()["title"] == "Refined Observation Drill"

    # Instance B: Approve candidate
    response_approve = client_b.post(
        f"/authoring/candidates/{candidate_id}/approve",
        headers={**HEADERS, "Accept": "application/json"},
    )
    assert response_approve.status_code == 200
    assert response_approve.json()["status"] == "approved"

    # Instance A: Candidate list shows approved status
    response_list = client_a.get(
        "/authoring/candidates",
        headers={**HEADERS, "Accept": "application/json"},
    )
    assert response_list.status_code == 200
    candidates = response_list.json()["candidates"]
    matched = [c for c in candidates if c["id"] == candidate_id]
    assert len(matched) == 1
    assert matched[0]["status"] == "approved"
    assert matched[0]["is_approved"] is True


def test_cross_instance_conflict_handling() -> None:
    client_a, client_b, _ = _create_paired_clients()

    # Generate candidate
    response_gen = client_a.post(
        "/authoring/generate",
        headers={**HEADERS, "Accept": "application/json"},
        json=BRIEF,
    )
    candidate_id = response_gen.json()["id"]

    # Instance A approves
    res_app = client_a.post(
        f"/authoring/candidates/{candidate_id}/approve",
        headers={**HEADERS, "Accept": "application/json"},
    )
    assert res_app.status_code == 200

    # Instance B attempts conflicting approval
    res_app_b = client_b.post(
        f"/authoring/candidates/{candidate_id}/approve",
        headers={**HEADERS, "Accept": "application/json"},
    )
    assert res_app_b.status_code == 409
    assert "already approved" in res_app_b.json()["detail"]

    # Instance B attempts conflicting rejection
    res_rej_b = client_b.post(
        f"/authoring/candidates/{candidate_id}/reject",
        headers={**HEADERS, "Accept": "application/json"},
    )
    assert res_rej_b.status_code == 409
    assert "cannot be rejected" in res_rej_b.json()["detail"]


def test_datastore_outage_returns_503_never_false_success() -> None:
    client_a, _, datastore_client = _create_paired_clients()

    # Successful generate
    response_gen = client_a.post(
        "/authoring/generate",
        headers={**HEADERS, "Accept": "application/json"},
        json=BRIEF,
    )
    candidate_id = response_gen.json()["id"]

    # Datastore write failure on approval
    datastore_client.fail_next_put = True
    res_app = client_a.post(
        f"/authoring/candidates/{candidate_id}/approve",
        headers={**HEADERS, "Accept": "application/json"},
    )
    assert res_app.status_code == 503
    assert "temporarily unavailable" in res_app.json()["detail"]

    # Datastore write failure on edit
    datastore_client.fail_next_put = True
    res_edit = client_a.post(
        f"/authoring/candidates/{candidate_id}/edit",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"title": "Failing Edit"},
    )
    assert res_edit.status_code == 503
    assert "temporarily unavailable" in res_edit.json()["detail"]

    # Datastore write failure on generate
    datastore_client.fail_next_put = True
    res_gen_fail = client_a.post(
        "/authoring/generate",
        headers={**HEADERS, "Accept": "application/json"},
        json=BRIEF,
    )
    assert res_gen_fail.status_code == 503
    assert "temporarily unavailable" in res_gen_fail.json()["detail"]

    # Datastore read failure on get
    datastore_client.fail_next_get = True
    res_get = client_a.get(
        f"/authoring/candidates/{candidate_id}",
        headers={**HEADERS, "Accept": "application/json"},
    )
    assert res_get.status_code == 503
    assert "temporarily unavailable" in res_get.json()["detail"]

    # Datastore query failure on list
    datastore_client.fail_query = True
    res_list = client_a.get(
        "/authoring/candidates",
        headers={**HEADERS, "Accept": "application/json"},
    )
    assert res_list.status_code == 503
    assert "temporarily unavailable" in res_list.json()["detail"]

    # Datastore query failure on workspace HTML
    datastore_client.fail_query = True
    res_workspace = client_a.get(
        "/authoring",
        headers={**HEADERS, "Accept": "text/html"},
    )
    assert res_workspace.status_code == 503
    assert "temporarily unavailable" in res_workspace.text


def test_learner_routes_are_isolated_from_authoring_state_and_outages() -> None:
    client, _, datastore_client = _create_paired_clients()

    # Generate candidate in authoring
    res_gen = client.post(
        "/authoring/generate",
        headers={**HEADERS, "Accept": "application/json"},
        json=BRIEF,
    )
    candidate_id = res_gen.json()["id"]

    # Learner routes do NOT expose candidate or authoring data
    dashboard_res = client.get("/")
    assert dashboard_res.status_code == 200
    assert candidate_id not in dashboard_res.text
    assert "Evidence-based observation" not in dashboard_res.text

    # Learner history route works
    history_res = client.get("/history")
    assert history_res.status_code == 200
    assert candidate_id not in history_res.text

    # Datastore authoring store outage
    datastore_client.fail_next_get = True
    datastore_client.fail_next_put = True
    datastore_client.fail_query = True

    # Learner routes continue to function normally
    learner_dash = client.get("/")
    assert learner_dash.status_code == 200

    learner_hist = client.get("/history")
    assert learner_hist.status_code == 200


def test_retention_window_in_web_responses() -> None:
    client_a, client_b, datastore_client = _create_paired_clients(retention_days=30)
    now = datetime.now(UTC)

    # Insert an expired unapproved candidate directly into datastore
    store_a = DatastoreAuthoringCandidateStore(datastore_client, retention_days=30)
    expired_candidate = _make_candidate(
        generated_at=now - timedelta(days=35),
        title="Old Unapproved Practice",
    )
    store_a.add(expired_candidate)

    # Fetching expired candidate returns 404
    res_get = client_b.get(
        f"/authoring/candidates/{expired_candidate.id}",
        headers={**HEADERS, "Accept": "application/json"},
    )
    assert res_get.status_code == 404

    # Listing candidates excludes expired candidate
    res_list = client_b.get(
        "/authoring/candidates",
        headers={**HEADERS, "Accept": "application/json"},
    )
    assert res_list.status_code == 200
    candidate_ids = [c["id"] for c in res_list.json()["candidates"]]
    assert str(expired_candidate.id) not in candidate_ids
