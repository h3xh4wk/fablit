"""Unit tests for the Stimulus domain models (SPEC-015)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import fablit.domain.stimulus
from fablit.domain import (
    ActivityStimulusContext,
    InvalidStimulusContextError,
    InvalidStimulusError,
    StimulusInstance,
)

from .helpers import make_stimulus, make_stimulus_context

STIMULUS_SOURCE = Path(fablit.domain.stimulus.__file__).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# ActivityStimulusContext (SPEC-015 §6)
# ---------------------------------------------------------------------------


def test_create_stimulus_context_with_valid_data() -> None:
    context = make_stimulus_context()

    assert context.learning_focus == "Composition"
    assert context.stimulus_context == "Fashion editorial photography"
    assert context.retrieval_query == "fashion editorial composition"


def test_stimulus_context_is_immutable() -> None:
    context = make_stimulus_context()

    with pytest.raises(FrozenInstanceError):
        context.learning_focus = "Colour"  # type: ignore[misc]


def test_reject_stimulus_context_without_learning_focus() -> None:
    with pytest.raises(InvalidStimulusContextError, match="learning focus"):
        make_stimulus_context(learning_focus="")


def test_reject_stimulus_context_with_blank_stimulus_context() -> None:
    with pytest.raises(InvalidStimulusContextError, match="stimulus context"):
        make_stimulus_context(stimulus_context="   ")


def test_reject_stimulus_context_without_retrieval_query() -> None:
    with pytest.raises(InvalidStimulusContextError, match="retrieval query"):
        make_stimulus_context(retrieval_query=None)


# ---------------------------------------------------------------------------
# StimulusInstance creation and identity (SPEC-015 §15–16)
# ---------------------------------------------------------------------------


def test_create_stimulus_instance_with_valid_data() -> None:
    activity_id = uuid4()
    retrieved_at = datetime.now(UTC) - timedelta(minutes=5)

    stimulus = make_stimulus(
        activity_id=activity_id,
        provider="wikimedia_commons",
        asset_id="Example.jpg",
        image_url="https://example.com/images/example.jpg",
        source_url="https://example.com/file/Example.jpg",
        creator="Jane Doe",
        license="CC BY-SA 4.0",
        attribution="Jane Doe / CC BY-SA 4.0",
        alt_text="A photograph for visual analysis.",
        retrieved_at=retrieved_at,
    )

    assert isinstance(stimulus.id, UUID)
    assert stimulus.activity_id == activity_id
    assert stimulus.provider == "wikimedia_commons"
    assert stimulus.asset_id == "Example.jpg"
    assert stimulus.image_url == "https://example.com/images/example.jpg"
    assert stimulus.source_url == "https://example.com/file/Example.jpg"
    assert stimulus.creator == "Jane Doe"
    assert stimulus.license == "CC BY-SA 4.0"
    assert stimulus.attribution == "Jane Doe / CC BY-SA 4.0"
    assert stimulus.alt_text == "A photograph for visual analysis."
    assert stimulus.retrieved_at == retrieved_at


def test_stimulus_instance_identity_is_unique_across_instances() -> None:
    assert make_stimulus().id != make_stimulus().id


def test_stimulus_instance_with_explicit_identity() -> None:
    stimulus_id = uuid4()

    stimulus = make_stimulus(id=stimulus_id)

    assert stimulus.id == stimulus_id


def test_stimulus_instance_identity_remains_stable() -> None:
    stimulus = make_stimulus()

    with pytest.raises(FrozenInstanceError):
        stimulus.id = uuid4()  # type: ignore[misc]


def test_reject_stimulus_without_identity() -> None:
    with pytest.raises(InvalidStimulusError, match="identity"):
        make_stimulus(id=None)


def test_reject_stimulus_with_invalid_identity() -> None:
    with pytest.raises(InvalidStimulusError, match="identity"):
        make_stimulus(id="not-a-uuid")


# ---------------------------------------------------------------------------
# Activity association (SPEC-015 §14, §47)
# ---------------------------------------------------------------------------


def test_stimulus_references_activity_by_identity() -> None:
    activity_id = uuid4()

    stimulus = make_stimulus(activity_id=activity_id)

    assert stimulus.activity_id == activity_id
    # The activity is referenced by identity only; it is not duplicated.
    assert not hasattr(stimulus, "activity")


def test_reject_stimulus_without_activity_reference() -> None:
    with pytest.raises(InvalidStimulusError, match="activity"):
        make_stimulus(activity_id=None)


def test_reject_stimulus_with_invalid_activity_reference() -> None:
    with pytest.raises(InvalidStimulusError, match="activity"):
        make_stimulus(activity_id="activity-1")


# ---------------------------------------------------------------------------
# Required metadata (SPEC-015 §16–17)
# ---------------------------------------------------------------------------


def test_stimulus_requires_provider() -> None:
    with pytest.raises(InvalidStimulusError, match="provider"):
        make_stimulus(provider="")


def test_stimulus_requires_direct_image_url() -> None:
    with pytest.raises(InvalidStimulusError, match="image url"):
        make_stimulus(image_url="   ")


def test_stimulus_requires_source_page_url() -> None:
    with pytest.raises(InvalidStimulusError, match="source page url"):
        make_stimulus(source_url="")


def test_stimulus_optional_metadata_may_be_absent() -> None:
    stimulus = make_stimulus(
        asset_id=None,
        creator=None,
        license=None,
        attribution=None,
        alt_text=None,
    )

    assert stimulus.asset_id is None
    assert stimulus.creator is None
    assert stimulus.license is None
    assert stimulus.attribution is None
    assert stimulus.alt_text is None


@pytest.mark.parametrize(
    "field",
    ["asset_id", "creator", "license", "attribution", "alt_text"],
)
def test_stimulus_rejects_blank_optional_metadata(field: str) -> None:
    with pytest.raises(InvalidStimulusError, match="non-blank"):
        make_stimulus(**{field: "   "})


# ---------------------------------------------------------------------------
# Retrieval timestamp (SPEC-015 §16)
# ---------------------------------------------------------------------------


def test_stimulus_records_retrieval_timestamp() -> None:
    retrieved_at = datetime.now(UTC) - timedelta(hours=1)

    stimulus = make_stimulus(retrieved_at=retrieved_at)

    assert stimulus.retrieved_at == retrieved_at
    assert stimulus.retrieved_at.tzinfo is not None


def test_reject_stimulus_without_retrieval_timestamp() -> None:
    with pytest.raises(InvalidStimulusError, match="when it was retrieved"):
        make_stimulus(retrieved_at=None)


def test_reject_stimulus_with_naive_retrieval_timestamp() -> None:
    with pytest.raises(InvalidStimulusError, match="timezone-aware"):
        make_stimulus(retrieved_at=datetime(2026, 8, 17, 12, 0, 0))


# ---------------------------------------------------------------------------
# Immutability (SPEC-015 §15)
# ---------------------------------------------------------------------------


def test_stimulus_cannot_be_silently_modified() -> None:
    stimulus = make_stimulus()

    with pytest.raises(FrozenInstanceError):
        stimulus.image_url = "https://changed.example/image.jpg"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        stimulus.attribution = "changed"  # type: ignore[misc]


def test_replace_cannot_create_invalid_stimulus() -> None:
    stimulus = make_stimulus()

    with pytest.raises(InvalidStimulusError, match="image url"):
        replace(stimulus, image_url="")


def test_replace_creates_a_new_stimulus_instance() -> None:
    stimulus = make_stimulus()

    updated = replace(stimulus, attribution="New attribution")

    assert updated.id == stimulus.id
    assert updated.attribution == "New attribution"
    assert stimulus.attribution is None


# ---------------------------------------------------------------------------
# Domain boundaries (SPEC-015 §39)
# ---------------------------------------------------------------------------


def test_stimulus_source_has_no_persistence_dependencies() -> None:
    for module in ("sqlalchemy", "psycopg", "redis", "sqlite3", "motor"):
        assert f"import {module}" not in STIMULUS_SOURCE
        assert f"from {module}" not in STIMULUS_SOURCE


def test_stimulus_source_has_no_framework_dependencies() -> None:
    for module in ("fastapi", "pydantic", "uvicorn"):
        assert f"import {module}" not in STIMULUS_SOURCE
        assert f"from {module}" not in STIMULUS_SOURCE


@pytest.mark.parametrize("forbidden", ["NIFT", "NID", "CEED"])
def test_stimulus_source_has_no_examination_specific_terminology(
    forbidden: str,
) -> None:
    assert forbidden.lower() not in STIMULUS_SOURCE.lower()


def test_stimulus_source_has_no_http_or_network_dependencies() -> None:
    assert "urllib" not in STIMULUS_SOURCE
    assert "requests" not in STIMULUS_SOURCE
    assert "http.client" not in STIMULUS_SOURCE


def test_stimulus_is_usable_in_memory_without_infrastructure() -> None:
    stimulus = make_stimulus()

    assert isinstance(stimulus, StimulusInstance)
    assert isinstance(make_stimulus_context(), ActivityStimulusContext)
