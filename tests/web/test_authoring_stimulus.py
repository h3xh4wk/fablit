"""Optional stimulus images and sketch evidence for authored practices.

SPEC-036: a generated candidate can carry one author-selected Pexafy image,
which follows publication into the learner practice and dashboard thumbnail.
SPEC-037: a published visual practice can offer the optional sketch input.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.main import create_app
from fablit.application.image_search import ImageCandidate, ImageSearchError
from fablit.config import load_config

SECRET = "authoring-stimulus-secret"
HEADERS = {"Authorization": f"Bearer {SECRET}"}
HTML_HEADERS = {**HEADERS, "Accept": "text/html"}
JSON_HEADERS = {**HEADERS, "Accept": "application/json"}

TITLE = "Still life observation"
IMAGE = ImageCandidate(
    photo_id="photo-1",
    image_url="https://cdn.example/large.jpg",
    thumbnail_url="https://cdn.example/thumb.jpg",
    alt_text="A pear and a silver box on a wooden table",
    description="A still life arrangement on a wooden table.",
    photographer="Saurabh_U",
    photographer_url="https://example/users/saurabh",
    source="Pixabay",
    source_url="https://example/photos/still-life",
    attribution="Photo by Saurabh_U on Pixabay",
    width=6000,
    height=4000,
    orientation="landscape",
    license_type="free",
)

BRIEF = {
    "practice_area": "Visual analysis",
    "learner_context": "A learner practising close observation.",
    "purpose": "Distinguish visible evidence from interpretation.",
    "intended_mode": "full-practice",
    "response_form": "A short written observation.",
    "evaluation_intent": "Look for specific observable details.",
    "feedback_intent": "Identify useful evidence and one next step.",
    "reflection_intent": "Notice which observation strategy was useful.",
    "stimulus_requirements": "A still life on a wooden table.",
}


class FakeImageSearch:
    def __init__(self, *, error: bool = False) -> None:
        self.queries: list[str] = []
        self._error = error

    def search(
        self, query: str, *, limit: int | None = None
    ) -> tuple[ImageCandidate, ...]:
        self.queries.append(query)
        if self._error:
            raise ImageSearchError("image search is unavailable")
        return (IMAGE,)


def _contract() -> dict[str, str]:
    return {
        "purpose": "Distinguish visible evidence from interpretation.",
        "task": "Identify three visible details. Explain what each suggests.",
        "expected_thinking": "Connect visible details directly to interpretations.",
        "response_contract": "Three concise bullet points citing evidence.",
        "evaluation_intent": "Check for concrete descriptive language.",
        "feedback_intent": "Highlight the most specific observation.",
        "reflection_intent": "Notice which visual feature guided your analysis.",
        "continuation_intent": "Apply the observation method to a contrasting scene.",
    }


def _client(
    *, image_search: FakeImageSearch | None = None
) -> tuple[TestClient, object]:
    app = create_app(
        load_config(
            overrides={
                "environment": "testing",
                "authoring_secret": SECRET,
                "practice_history_repository": "memory",
            }
        )
    )
    provider = Mock()
    provider.generate.return_value = SimpleNamespace(
        candidate_data={
            "title": TITLE,
            "description": "Describe what the image shows.",
            "stimulus_query": "a still life with fruit on a wooden table",
            "contract": _contract(),
        },
        provider="test-provider",
        model="test-model",
        generated_at=datetime.now(UTC),
    )
    app.state.authoring_ai_provider = provider
    app.state.authoring_image_search = image_search
    return TestClient(app), app


def _generate(client: TestClient) -> tuple[str, str]:
    response = client.post("/authoring/generate", headers=HTML_HEADERS, data=BRIEF)
    assert response.status_code == 200, response.text
    match = re.search(r"/authoring/candidates/([0-9a-f-]+)", response.text)
    assert match is not None
    return match.group(1), response.text


def _approve(client: TestClient, candidate_id: str) -> None:
    response = client.post(
        f"/authoring/candidates/{candidate_id}/approve", headers=HEADERS
    )
    assert response.status_code == 200, response.text


def _publish(client: TestClient, candidate_id: str) -> None:
    response = client.post(
        f"/authoring/candidates/{candidate_id}/publish", headers=JSON_HEADERS
    )
    assert response.status_code == 200, response.text


def _dashboard_href(client: TestClient) -> str:
    page = client.get("/").text
    for card in re.findall(r'<li class="card">.*?</li>', page, re.DOTALL):
        if TITLE in card:
            match = re.search(r'href="(/activities/[0-9a-f-]+)', card)
            assert match is not None
            return match.group(1)
    raise AssertionError("no dashboard card for the published practice")


def test_generate_lists_pexafy_options_and_attribution() -> None:
    search = FakeImageSearch()
    client, _ = _client(image_search=search)

    candidate_id, page = _generate(client)

    assert search.queries == ["a still life with fruit on a wooden table"]
    assert "Stimulus image" in page
    assert "https://cdn.example/thumb.jpg" in page
    assert "Saurabh_U" in page
    assert "Use this image" in page
    assert f"/authoring/candidates/{candidate_id}/stimulus" in page


def test_selecting_and_clearing_an_image_revises_the_candidate() -> None:
    client, _ = _client(image_search=FakeImageSearch())
    candidate_id, _ = _generate(client)

    selected = client.post(
        f"/authoring/candidates/{candidate_id}/stimulus",
        headers=HTML_HEADERS,
        data={"photo_id": "photo-1"},
    )

    assert selected.status_code == 200
    assert "https://cdn.example/large.jpg" in selected.text
    assert "Remove image" in selected.text
    assert "will use this image" in selected.text
    assert "Revision 2" in selected.text

    cleared = client.post(
        f"/authoring/candidates/{candidate_id}/stimulus",
        headers=HTML_HEADERS,
        data={"photo_id": ""},
    )

    assert cleared.status_code == 200
    assert "has no stimulus image" in cleared.text
    assert "Remove image" not in cleared.text
    assert "Revision 3" in cleared.text


def test_unknown_image_selection_is_refused() -> None:
    client, _ = _client(image_search=FakeImageSearch())
    candidate_id, _ = _generate(client)

    response = client.post(
        f"/authoring/candidates/{candidate_id}/stimulus",
        headers=HTML_HEADERS,
        data={"photo_id": "not-an-option"},
    )

    assert response.status_code == 422
    assert "no longer one of this candidate" in response.text


def test_search_failure_does_not_block_candidate_generation() -> None:
    client, _ = _client(image_search=FakeImageSearch(error=True))

    candidate_id, page = _generate(client)

    assert candidate_id
    assert "No images were available" in page
    assert "a still life with fruit on a wooden table" in page


def test_published_image_is_the_learner_stimulus_and_thumbnail() -> None:
    client, _ = _client(image_search=FakeImageSearch())
    candidate_id, _ = _generate(client)
    client.post(
        f"/authoring/candidates/{candidate_id}/stimulus",
        headers=HEADERS,
        data={"photo_id": "photo-1"},
    )
    _approve(client, candidate_id)
    _publish(client, candidate_id)

    dashboard = client.get("/")
    assert IMAGE.thumbnail_url not in dashboard.text
    assert IMAGE.image_url in dashboard.text

    href = _dashboard_href(client)
    practice = client.get(href)

    assert practice.status_code == 200
    assert IMAGE.image_url in practice.text
    assert IMAGE.alt_text in practice.text
    assert "Saurabh_U" in practice.text
    assert 'name="artifact"' in practice.text


def test_sketch_can_be_turned_off_before_publication() -> None:
    client, _ = _client(image_search=FakeImageSearch())
    candidate_id, _ = _generate(client)
    client.post(
        f"/authoring/candidates/{candidate_id}/stimulus",
        headers=HEADERS,
        data={"photo_id": "photo-1"},
    )

    edited = client.post(
        f"/authoring/candidates/{candidate_id}/edit",
        headers=HTML_HEADERS,
        data={"allow_sketch_present": "1"},
    )
    assert edited.status_code == 200, edited.text
    _approve(client, candidate_id)
    _publish(client, candidate_id)

    practice = client.get(_dashboard_href(client))

    assert practice.status_code == 200
    assert IMAGE.image_url in practice.text
    assert 'name="artifact"' not in practice.text


def test_uploaded_sketch_on_a_published_practice_is_readable_in_history() -> None:
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    client, _ = _client(image_search=FakeImageSearch())
    candidate_id, _ = _generate(client)
    client.post(
        f"/authoring/candidates/{candidate_id}/stimulus",
        headers=HEADERS,
        data={"photo_id": "photo-1"},
    )
    _approve(client, candidate_id)
    _publish(client, candidate_id)
    href = _dashboard_href(client)

    client.post(href + "/intention", data={"intention": ""})
    submitted = client.post(
        href + "/submit",
        data={"response": "The pear and the silver box hold the arrangement."},
        files={"artifact": ("my-sketch.png", png, "image/png")},
    )
    assert submitted.status_code == 200, submitted.text
    client.post("/reflect", data={"content": "I noticed the light first."})

    history = client.get("/history")
    assert TITLE in history.text
    review_href = next(
        line.split('href="')[1].split('"')[0]
        for line in history.text.splitlines()
        if 'href="/history/' in line
    )
    review = client.get(review_href)
    artifact = client.get(review_href + "/artifact")

    assert review.status_code == 200
    assert review_href + "/artifact" in review.text
    assert artifact.status_code == 200
    assert artifact.content == png
