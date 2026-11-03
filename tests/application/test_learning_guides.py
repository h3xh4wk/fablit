"""Application tests for the Learning Guides content model (SPEC-045).

These tests pin the behaviour learners and authors depend on: sections keep
their configured order, only complete and safely attributed content publishes,
editing published content returns it to draft, and a guide is discoverable
from every practice it supports.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from fablit.application.errors import (
    InvalidLearningGuideError,
    LearningGuideNotPublishableError,
)
from fablit.application.image_search import ImageCandidate
from fablit.application.learning_guides import (
    GuideImage,
    GuideLayout,
    GuideSection,
    GuideStage,
    GuideStatus,
    InMemoryLearningGuideRepository,
    LearningGuide,
    add_section,
    archive_guide,
    move_section,
    pilot_guides,
    publish_guide,
    remove_image,
    remove_section,
    save_guide_details,
    seed_pilot_guides,
    select_image,
    set_search_candidates,
    update_image,
    update_section,
    validate_guide,
)

PRACTICE_ID = uuid4()


def _candidate(photo_id: str = "photo-1", **overrides: object) -> ImageCandidate:
    values: dict[str, object] = {
        "photo_id": photo_id,
        "image_url": f"https://cdn.example/{photo_id}-large.jpg",
        "thumbnail_url": f"https://cdn.example/{photo_id}-thumb.jpg",
        "alt_text": "A hand sorting produce at a market stall",
        "description": "A market stall at dawn.",
        "photographer": "A. Photographer",
        "photographer_url": "https://example/photographers/a",
        "source": "Pixabay",
        "source_url": f"https://example/photos/{photo_id}",
        "attribution": "Photo by A. Photographer on Pixabay",
        "width": 4000,
        "height": 3000,
        "orientation": "landscape",
        "license_type": "free",
    }
    values.update(overrides)
    return ImageCandidate(**values)  # type: ignore[arg-type]


def _section(
    stage: GuideStage = GuideStage.OBSERVE,
    heading: str = "Look beyond what is immediately visible",
    body: str = "Notice the work that happens before others arrive.",
) -> GuideSection:
    return GuideSection(stage=stage, heading=heading, body=body)


def _guide(
    *,
    sections: tuple[GuideSection, ...] | None = None,
    practice_id: UUID | None = PRACTICE_ID,
    **overrides: object,
) -> LearningGuide:
    return LearningGuide(
        title="Finding stories in everyday surroundings",
        summary="A guided way into observation and photography.",
        practice_area="Observation and photography",
        sections=(_section(),) if sections is None else sections,
        associated_practice_ids=(practice_id,) if practice_id else (),
        **overrides,  # type: ignore[arg-type]
    )


def _repository(guide: LearningGuide) -> InMemoryLearningGuideRepository:
    repository = InMemoryLearningGuideRepository()
    repository.save(guide)
    return repository


def test_new_guide_is_an_unpublished_draft_with_a_stable_identity() -> None:
    guide = _guide()

    assert guide.status is GuideStatus.DRAFT
    assert guide.is_published is False
    assert guide.version == 1
    assert guide.published_at is None
    assert guide.created_at.tzinfo is not None


def test_guide_requires_a_learner_facing_title() -> None:
    with pytest.raises(InvalidLearningGuideError):
        LearningGuide(title="  ", summary="", practice_area="")


def test_sections_keep_their_configured_order_when_moved() -> None:
    first = _section(heading="Observe")
    second = _section(stage=GuideStage.THINK, heading="Think")
    third = _section(stage=GuideStage.CREATE, heading="Create")

    guide = _guide(sections=(first, second, third))
    guide = move_section(guide, third.id, -1)
    assert [section.heading for section in guide.sections] == [
        "Observe",
        "Create",
        "Think",
    ]

    guide = move_section(guide, first.id, 1)
    assert [section.heading for section in guide.sections] == [
        "Create",
        "Observe",
        "Think",
    ]


def test_moving_a_section_past_the_edge_keeps_the_order() -> None:
    first = _section(heading="Observe")
    guide = _guide(sections=(first,))

    assert move_section(guide, first.id, -1).sections == guide.sections
    assert move_section(guide, first.id, 1).sections == guide.sections


def test_removing_a_section_is_idempotent() -> None:
    first = _section(heading="Observe")
    second = _section(stage=GuideStage.THINK, heading="Think")
    guide = _guide(sections=(first, second))

    once = remove_section(guide, first.id)
    twice = remove_section(once, first.id)

    assert [section.heading for section in once.sections] == ["Think"]
    assert twice == once


def test_updating_a_section_keeps_its_position_and_identity() -> None:
    first = _section(heading="Observe")
    second = _section(stage=GuideStage.THINK, heading="Think")
    guide = _guide(sections=(first, second))

    updated = update_section(
        guide,
        GuideSection(
            id=first.id,
            stage=GuideStage.OBSERVE,
            heading="Observe more slowly",
            body="Stay with one detail for a full minute.",
        ),
    )

    assert updated.sections[0].id == first.id
    assert updated.sections[0].heading == "Observe more slowly"
    assert updated.sections[1].heading == "Think"


def test_unsupported_layout_falls_back_to_the_default_with_a_warning() -> None:
    section = GuideSection(
        heading="A section",
        body="Content.",
        layout="carousel-of-doom",
    )

    assert section.resolved_layout is GuideLayout.DEFAULT
    validation = validate_guide(_guide(sections=(section,)))
    assert any("unsupported layout" in warning for warning in validation.warnings)


def test_publication_requires_summary_area_and_a_section() -> None:
    guide = LearningGuide(
        title="An incomplete guide",
        summary="",
        practice_area="",
        sections=(),
    )

    validation = validate_guide(guide)

    assert validation.is_publishable is False
    assert any("summary" in error for error in validation.errors)
    assert any("practice area" in error for error in validation.errors)
    assert any("at least one section" in error for error in validation.errors)


def test_publication_refuses_an_association_with_a_missing_practice() -> None:
    guide = _guide()

    validation = validate_guide(guide, known_practice_ids={uuid4()})

    assert validation.is_publishable is False
    assert any("not an available practice" in error for error in validation.errors)


def test_no_practice_association_is_a_warning_not_an_error() -> None:
    validation = validate_guide(_guide(practice_id=None))

    assert validation.is_publishable is True
    assert any(
        "no practice is associated" in warning for warning in validation.warnings
    )


def test_image_without_alt_text_cannot_be_published() -> None:
    section = _section()
    guide = _guide(sections=(section,))
    guide = set_search_candidates(guide, section.id, (_candidate(),), query="market")
    guide = select_image(guide, section.id, photo_id="photo-1", alt_text="")
    # The candidate carried alt text, so blank author alt text falls back to it.
    assert guide.sections[0].images[0].alt_text

    image = guide.sections[0].images[0]
    broken = GuideImage(
        provider=image.provider,
        asset_id=image.asset_id,
        image_url=image.image_url,
        source_url=image.source_url,
        creator=image.creator,
        source=image.source,
        attribution=image.attribution,
        alt_text="",
    )
    guide = update_section(
        guide,
        GuideSection(id=section.id, heading="Look", body="Notice.", images=(broken,)),
    )

    validation = validate_guide(guide)
    assert any("alternative text" in error for error in validation.errors)


def test_image_without_attribution_cannot_be_published() -> None:
    section = _section()
    guide = _guide(sections=(section,))
    guide = set_search_candidates(
        guide,
        section.id,
        (_candidate(photographer="", attribution=""),),
        query="market",
    )
    guide = select_image(guide, section.id, photo_id="photo-1")

    validation = validate_guide(guide)

    assert validation.is_publishable is False
    assert any(
        "lacks creator, source, or attribution" in error for error in validation.errors
    )


def test_image_rejects_a_non_web_url() -> None:
    with pytest.raises(InvalidLearningGuideError):
        GuideImage(
            provider="pexafy",
            asset_id="photo-1",
            image_url="file:///etc/passwd",
            source_url="https://example/photos/1",
        )


def test_publishing_sets_status_version_and_time() -> None:
    guide = _guide()
    repository = _repository(guide)
    now = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)

    published = publish_guide(
        guide,
        repository=repository,
        known_practice_ids={PRACTICE_ID},
        now=now,
    )

    assert published.is_published
    assert published.version == 1
    assert published.published_at == now
    assert repository.get(guide.id) == published


def test_publishing_is_refused_without_complete_content() -> None:
    guide = LearningGuide(
        title="An incomplete guide",
        summary="",
        practice_area="",
        sections=(),
    )
    repository = _repository(guide)

    with pytest.raises(LearningGuideNotPublishableError):
        publish_guide(guide, repository=repository, known_practice_ids={PRACTICE_ID})


def test_publishing_the_same_guide_again_is_idempotent() -> None:
    guide = _guide()
    repository = _repository(guide)
    published = publish_guide(
        guide, repository=repository, known_practice_ids={PRACTICE_ID}
    )

    repeated = publish_guide(
        published, repository=repository, known_practice_ids={PRACTICE_ID}
    )

    assert repeated == published


def test_editing_published_content_returns_it_to_draft() -> None:
    guide = _guide()
    repository = _repository(guide)
    published = publish_guide(
        guide, repository=repository, known_practice_ids={PRACTICE_ID}
    )

    edited = save_guide_details(
        published,
        title="A revised title",
        summary=published.summary,
        practice_area=published.practice_area,
        associated_practice_ids=published.associated_practice_ids,
    )

    assert edited.status is GuideStatus.DRAFT
    assert edited.version == published.version

    # Once the draft edit is saved, the guide leaves learner visibility until
    # it is explicitly republished.
    repository.save(edited)
    assert repository.published() == ()


def test_republishing_after_an_edit_bumps_the_content_version() -> None:
    guide = _guide()
    repository = _repository(guide)
    first = publish_guide(
        guide, repository=repository, known_practice_ids={PRACTICE_ID}
    )

    edited = save_guide_details(
        first,
        title="A revised title",
        summary=first.summary,
        practice_area=first.practice_area,
        associated_practice_ids=first.associated_practice_ids,
    )
    second = publish_guide(
        edited, repository=repository, known_practice_ids={PRACTICE_ID}
    )

    assert second.version == first.version + 1
    assert second.is_published


def test_archiving_removes_the_guide_from_learner_visibility() -> None:
    guide = _guide()
    repository = _repository(guide)
    published = publish_guide(
        guide, repository=repository, known_practice_ids={PRACTICE_ID}
    )

    archived = archive_guide(published, repository=repository)

    assert archived.is_archived
    assert repository.published() == ()
    assert repository.published_for_practice(PRACTICE_ID) == ()


def test_archived_guides_cannot_be_republished() -> None:
    original = _guide()
    repository = _repository(original)
    guide = archive_guide(original, repository=repository)

    with pytest.raises(LearningGuideNotPublishableError):
        publish_guide(
            guide,
            repository=repository,
            known_practice_ids={PRACTICE_ID},
        )


def test_a_published_guide_is_discoverable_from_every_associated_practice() -> None:
    other_practice = uuid4()
    guide = _guide()
    guide = save_guide_details(
        guide,
        title=guide.title,
        summary=guide.summary,
        practice_area=guide.practice_area,
        associated_practice_ids=(PRACTICE_ID, other_practice),
    )
    repository = _repository(guide)
    publish_guide(
        guide,
        repository=repository,
        known_practice_ids={PRACTICE_ID, other_practice},
    )

    assert repository.published_for_practice(PRACTICE_ID)
    assert repository.published_for_practice(other_practice)
    assert repository.published_for_practice(uuid4()) == ()


def test_selecting_an_image_retains_provider_provenance() -> None:
    section = _section()
    guide = _guide(sections=(section,))
    guide = set_search_candidates(guide, section.id, (_candidate(),), query="market")

    guide = select_image(
        guide,
        section.id,
        photo_id="photo-1",
        caption="Produce sorted before opening.",
    )

    image = guide.sections[0].images[0]
    assert image.provider == "pexafy"
    assert image.asset_id == "photo-1"
    assert image.creator == "A. Photographer"
    assert image.source == "Pixabay"
    assert image.attribution.startswith("Photo by A. Photographer")
    assert image.license_type == "free"
    assert image.query == "market"
    assert image.caption == "Produce sorted before opening."
    assert image.has_provenance is True

    removed = remove_image(guide, section.id, asset_id="photo-1")
    assert removed.sections[0].images == ()


def test_selecting_an_unlisted_candidate_is_refused() -> None:
    section = _section()
    guide = _guide(sections=(section,))
    guide = set_search_candidates(guide, section.id, (_candidate(),), query="market")

    with pytest.raises(InvalidLearningGuideError):
        select_image(guide, section.id, photo_id="not-shown")


def test_search_results_never_unpublish_a_guide() -> None:
    guide = _guide()
    repository = _repository(guide)
    published = publish_guide(
        guide, repository=repository, known_practice_ids={PRACTICE_ID}
    )

    searched = set_search_candidates(
        published,
        published.sections[0].id,
        (_candidate(),),
        query="market",
    )

    assert searched.is_published


def test_adding_a_section_keeps_authorship_evidence_and_unsets_draft() -> None:
    guide = _guide(sections=())
    section = _section(stage=GuideStage.REFLECT, heading="Reflect")

    added = add_section(guide, section)

    assert added.sections == (section,)
    assert added.status is GuideStatus.DRAFT
    assert added.updated_at >= guide.updated_at


def test_guide_image_display_and_preview_urls_distinguish_learner_and_authoring() -> (
    None
):
    image = GuideImage.from_candidate(_candidate("photo-1"))

    assert image.display_url == "https://cdn.example/photo-1-large.jpg"
    assert image.preview_url == "https://cdn.example/photo-1-thumb.jpg"


def test_section_suggested_search_query_falls_back_to_heading() -> None:
    section = _section(heading="  Look   beyond what is visible  ")
    assert section.suggested_search_query == "Look beyond what is visible"

    searched = GuideSection(
        heading="Look beyond",
        body="Body.",
        search_query="custom market query",
    )
    assert searched.suggested_search_query == "custom market query"


def test_updating_and_replacing_a_selected_section_image() -> None:
    section = _section()
    guide = _guide(sections=(section,))
    candidates = (_candidate("photo-1"), _candidate("photo-2"))
    guide = set_search_candidates(guide, section.id, candidates, query="market")
    guide = select_image(
        guide,
        section.id,
        photo_id="photo-1",
        alt_text="Original alt",
        caption="Original caption",
    )

    refined = update_image(
        guide,
        section.id,
        asset_id="photo-1",
        alt_text="Refined alt text",
        caption="Refined caption",
    )
    assert refined.sections[0].images[0].alt_text == "Refined alt text"
    assert refined.sections[0].images[0].caption == "Refined caption"

    replaced = select_image(
        refined,
        section.id,
        photo_id="photo-2",
        alt_text="Replacement alt",
        caption="Replacement caption",
        replace_asset_id="photo-1",
    )
    assert len(replaced.sections[0].images) == 1
    assert replaced.sections[0].images[0].asset_id == "photo-2"
    assert replaced.sections[0].images[0].alt_text == "Replacement alt"

    with pytest.raises(InvalidLearningGuideError):
        update_image(
            replaced,
            section.id,
            asset_id="photo-1",
            alt_text="Missing",
        )


def test_seeding_pilot_guides_is_idempotent_and_publishable() -> None:
    repository = InMemoryLearningGuideRepository()
    guides = pilot_guides()
    assert len(guides) == 5

    seeded = seed_pilot_guides(repository)
    assert len(seeded) == 5
    assert len(repository.list_guides()) == 5

    # Every pilot guide covers the Observe-Think-Explore-Create sequence and is
    # ready for publication once reviewed.
    layouts_seen: set[GuideLayout] = set()
    for item in seeded:
        assert item.status is GuideStatus.DRAFT
        assert validate_guide(item).is_publishable
        for sec in item.sections:
            layouts_seen.add(sec.resolved_layout)
    assert len(layouts_seen) >= 4

    # Seeding a second time does not duplicate or overwrite existing guides.
    assert seed_pilot_guides(repository) == ()
    assert len(repository.list_guides()) == 5
