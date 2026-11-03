"""Datastore-backed learning guide store tests (SPEC-045).

The adapter must round-trip full guide content — including long section text
and image provenance — without tripping Datastore's indexed-value limit, and
it must surface storage failures rather than reporting a guide as saved.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from fablit.application.image_search import ImageCandidate
from fablit.application.learning_guides import (
    GuideImage,
    GuideSection,
    GuideStage,
    LearningGuide,
    publish_guide,
)
from fablit.application.persistence import PersistenceError
from fablit.platform.datastore_learning_guide_store import (
    LEARNING_GUIDE_KIND,
    DatastoreLearningGuideStore,
)
from tests.persistence.datastore_fakes import (
    FakeEntity,
    FakeKey,
    assert_within_index_limits,
)

PRACTICE_ID = uuid4()


class FakeQuery:
    def __init__(self, client: FakeDatastoreClient, kind: str, namespace: str) -> None:
        self._client = client
        self._kind = kind
        self._namespace = namespace

    def fetch(self) -> list[FakeEntity]:
        if self._client.fail_query:
            raise RuntimeError("simulated datastore query outage")
        return [
            entity
            for entity in self._client.store.values()
            if entity.key is not None
            and entity.key.kind == self._kind
            and entity.key.namespace == self._namespace
        ]


class FakeDatastoreClient:
    """Minimal Datastore client double with the shared index-limit check."""

    def __init__(self) -> None:
        self.store: dict[tuple[str, str, str | None], FakeEntity] = {}
        self.fail_put = False
        self.fail_query = False
        self.fail_get = False

    def key(self, kind: str, name: str, namespace: str | None = None) -> FakeKey:
        return FakeKey(kind, name, namespace)

    def entity(
        self, key: FakeKey | None = None, exclude_from_indexes: Any = ()
    ) -> FakeEntity:
        return FakeEntity(key, exclude_from_indexes)

    def put(self, entity: FakeEntity) -> None:
        assert_within_index_limits(entity)
        if self.fail_put:
            raise RuntimeError("simulated datastore write outage")
        assert entity.key is not None
        self.store[entity.key._id()] = entity

    def get(self, key: FakeKey) -> FakeEntity | None:
        if self.fail_get:
            raise RuntimeError("simulated datastore read outage")
        return self.store.get(key._id())

    def query(self, kind: str, namespace: str | None = None) -> FakeQuery:
        return FakeQuery(self, kind, namespace or "")


def _candidate() -> ImageCandidate:
    return ImageCandidate(
        photo_id="photo-1",
        image_url="https://cdn.example/large.jpg",
        thumbnail_url="https://cdn.example/thumb.jpg",
        alt_text="A hand sorting produce at a market stall",
        description="A market stall at dawn.",
        photographer="A. Photographer",
        photographer_url="https://example/photographers/a",
        source="Pixabay",
        source_url="https://example/photos/market",
        attribution="Photo by A. Photographer on Pixabay",
        width=4000,
        height=3000,
        orientation="landscape",
        license_type="free",
    )


def _image() -> GuideImage:
    return GuideImage.from_candidate(
        _candidate(), caption="Produce sorted before opening.", query="market"
    )


def _section(
    *, body: str = "Notice who prepares the space before others arrive."
) -> GuideSection:
    return GuideSection(
        stage=GuideStage.OBSERVE,
        heading="Look beyond what is immediately visible",
        body=body,
        questions=("What would someone normally overlook?",),
        examples=("A close-up of hands at work.",),
        reflection_prompt="What did you notice that you would have missed?",
        layout="split",
        images=(_image(),),
        search_query="market hands",
        search_candidates=(_candidate(),),
    )


def _guide(**overrides: object) -> LearningGuide:
    values: dict[str, object] = {
        "title": "Finding stories in everyday surroundings",
        "summary": "A guided way into observation and photography.",
        "practice_area": "Observation and photography",
        "intended_learner_context": "A learner approaching an open-ended prompt.",
        "sections": (_section(),),
        "associated_practice_ids": (PRACTICE_ID,),
        "created_at": datetime(2026, 11, 1, 9, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 11, 2, 9, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return LearningGuide(**values)  # type: ignore[arg-type]


def test_round_trip_preserves_content_and_provenance() -> None:
    client = FakeDatastoreClient()
    store = DatastoreLearningGuideStore(client)
    guide = _guide()

    store.save(guide)
    restored = store.get(guide.id)

    assert restored == guide
    assert restored is not None
    image = restored.sections[0].images[0]
    assert image.creator == "A. Photographer"
    assert image.source == "Pixabay"
    assert image.attribution.startswith("Photo by A. Photographer")
    assert image.query == "market"
    assert restored.sections[0].search_candidates[0].photo_id == "photo-1"


def test_long_section_text_is_stored_without_index_limits() -> None:
    client = FakeDatastoreClient()
    store = DatastoreLearningGuideStore(client)
    long_body = "Observation " * 1000

    guide = _guide(sections=(_section(body=long_body),))
    store.save(guide)
    restored = store.get(guide.id)

    assert restored is not None
    assert restored.sections[0].body == long_body.strip()
    assert len(restored.sections[0].body) > 1500


def test_get_returns_none_for_an_unknown_guide() -> None:
    store = DatastoreLearningGuideStore(FakeDatastoreClient())

    assert store.get(uuid4()) is None


def test_save_failure_is_reported_as_a_persistence_error() -> None:
    client = FakeDatastoreClient()
    client.fail_put = True
    store = DatastoreLearningGuideStore(client)

    with pytest.raises(PersistenceError):
        store.save(_guide())


def test_read_failure_is_reported_as_a_persistence_error() -> None:
    client = FakeDatastoreClient()
    client.fail_get = True
    store = DatastoreLearningGuideStore(client)

    with pytest.raises(PersistenceError):
        store.get(uuid4())


def test_query_failure_is_reported_as_a_persistence_error() -> None:
    client = FakeDatastoreClient()
    client.fail_query = True
    store = DatastoreLearningGuideStore(client)

    with pytest.raises(PersistenceError):
        store.list_guides()


def test_corrupt_payload_is_reported_rather_than_reported_as_empty() -> None:
    client = FakeDatastoreClient()
    store = DatastoreLearningGuideStore(client)
    guide_id = uuid4()
    key = client.key(LEARNING_GUIDE_KIND, str(guide_id), namespace="guides")
    entity = client.entity(key)
    entity.update({"status": "published", "payload": "not-a-mapping"})
    client.store[key._id()] = entity

    with pytest.raises(PersistenceError):
        store.get(guide_id)


def test_list_guides_returns_published_and_archived_guides_newest_first() -> None:
    client = FakeDatastoreClient()
    store = DatastoreLearningGuideStore(client)
    older = _guide(title="Older guide")
    newer = _guide(
        title="Newer guide",
        updated_at=datetime(2026, 11, 3, 9, 0, tzinfo=UTC),
    )
    store.save(older)
    store.save(newer)

    guides = store.list_guides()

    assert [guide.title for guide in guides] == ["Newer guide", "Older guide"]
    assert store.published() == ()


def test_publishing_a_restored_guide_keeps_its_identity() -> None:
    client = FakeDatastoreClient()
    store = DatastoreLearningGuideStore(client)
    guide = _guide()
    store.save(guide)

    restored = store.get(guide.id)
    assert restored is not None
    published = publish_guide(
        restored, repository=store, known_practice_ids={PRACTICE_ID}
    )

    assert store.get(published.id) is not None
    assert store.get(published.id) == published
    assert store.published_for_practice(PRACTICE_ID)[0].version == 1


def test_guide_identity_is_used_as_the_entity_key() -> None:
    client = FakeDatastoreClient()
    store = DatastoreLearningGuideStore(client)
    guide = _guide()

    store.save(guide)

    key = (LEARNING_GUIDE_KIND, str(guide.id), "guides")
    assert key in client.store
