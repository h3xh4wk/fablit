"""Unit tests for the Skill domain model (SPEC-010)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import fablit.domain.skill
from fablit.domain import (
    InvalidSkillError,
    Skill,
)

from .helpers import make_skill

SKILL_SOURCE = Path(fablit.domain.skill.__file__).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Creation and identity (FR-001 / DR-001)
# ---------------------------------------------------------------------------


def test_create_skill_with_valid_data() -> None:
    skill = make_skill(
        name="Visual Analysis",
        description="The ability to observe and interpret visual information.",
    )

    assert isinstance(skill.id, UUID)
    assert skill.name == "Visual Analysis"
    assert (
        skill.description == "The ability to observe and interpret visual information."
    )


def test_create_skill_with_generated_identity() -> None:
    skill = make_skill()

    assert isinstance(skill.id, UUID)


def test_skill_identity_is_unique_across_instances() -> None:
    first = make_skill()
    second = make_skill()

    assert first.id != second.id


def test_skill_identity_remains_stable() -> None:
    skill = make_skill()
    original_id = skill.id

    assert skill.id == original_id
    with pytest.raises(FrozenInstanceError):
        skill.id = uuid4()  # type: ignore[misc]


def test_skill_with_explicit_identity() -> None:
    skill_id = uuid4()

    skill = make_skill(id=skill_id)

    assert skill.id == skill_id


def test_reject_skill_without_identity() -> None:
    with pytest.raises(InvalidSkillError, match="identity"):
        make_skill(id=None)


def test_reject_skill_with_invalid_identity() -> None:
    with pytest.raises(InvalidSkillError, match="identity"):
        make_skill(id="not-a-uuid")


# ---------------------------------------------------------------------------
# Name validity (FR-002 / DR-002 / DR-004)
# ---------------------------------------------------------------------------


def test_create_skill_with_meaningful_name() -> None:
    name = "Communication"

    skill = make_skill(name=name)

    assert skill.name == name


def test_reject_skill_without_name() -> None:
    with pytest.raises(InvalidSkillError, match="name"):
        make_skill(name=None)


def test_reject_skill_with_empty_name() -> None:
    with pytest.raises(InvalidSkillError, match="name"):
        make_skill(name="")


def test_reject_skill_with_whitespace_only_name() -> None:
    with pytest.raises(InvalidSkillError, match="name"):
        make_skill(name="   \n\t ")


def test_reject_skill_with_non_string_name() -> None:
    with pytest.raises(InvalidSkillError, match="name"):
        make_skill(name=42)


# ---------------------------------------------------------------------------
# Description validity (FR-003 / DR-003 / DR-005)
# ---------------------------------------------------------------------------


def test_create_skill_with_meaningful_description() -> None:
    description = "The ability to convey ideas clearly and effectively."

    skill = make_skill(description=description)

    assert skill.description == description


def test_reject_skill_without_description() -> None:
    with pytest.raises(InvalidSkillError, match="description"):
        make_skill(description=None)


def test_reject_skill_with_empty_description() -> None:
    with pytest.raises(InvalidSkillError, match="description"):
        make_skill(description="")


def test_reject_skill_with_whitespace_only_description() -> None:
    with pytest.raises(InvalidSkillError, match="description"):
        make_skill(description="   \n\t ")


def test_reject_skill_with_non_string_description() -> None:
    with pytest.raises(InvalidSkillError, match="description"):
        make_skill(description=42)


# ---------------------------------------------------------------------------
# Immutability (FR-004 / DR-006)
# ---------------------------------------------------------------------------


def test_skill_cannot_be_silently_modified() -> None:
    skill = make_skill()

    with pytest.raises(FrozenInstanceError):
        skill.name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        skill.description = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        skill.id = uuid4()  # type: ignore[misc]


def test_replace_cannot_create_invalid_skill() -> None:
    skill = make_skill()

    with pytest.raises(InvalidSkillError, match="name"):
        replace(skill, name="")
    with pytest.raises(InvalidSkillError, match="description"):
        replace(skill, description="")


# ---------------------------------------------------------------------------
# Activity independence (FR-005 / DR-007 / DR-008)
# ---------------------------------------------------------------------------


def test_skill_does_not_require_an_assessment_activity() -> None:
    skill = make_skill()

    # A Skill can exist without any Assessment Activity.
    assert isinstance(skill, Skill)
    assert not hasattr(skill, "activity_id")
    assert not hasattr(skill, "activity")


def test_skill_is_not_restricted_to_a_single_activity() -> None:
    skill = make_skill()

    # No single-activity ownership field exists in the model.
    assert not hasattr(skill, "activity_id")
    assert not hasattr(skill, "activity_ids")


# ---------------------------------------------------------------------------
# No evaluation criteria (FR-008 / DR-009 / DR-010)
# ---------------------------------------------------------------------------


def test_skill_does_not_contain_evaluation_criteria() -> None:
    skill = make_skill()

    assert not hasattr(skill, "criteria")
    assert not hasattr(skill, "rubric")
    # A Skill without evaluation criteria is valid.
    assert isinstance(skill, Skill)


# ---------------------------------------------------------------------------
# No Progress / mastery / scoring state (FR-009 / FR-010 / DR-010 / DR-011)
# ---------------------------------------------------------------------------


def test_skill_has_no_scoring_state() -> None:
    skill = make_skill()

    assert not hasattr(skill, "score")
    assert not hasattr(skill, "percentage")
    assert not hasattr(skill, "grade")
    assert not hasattr(skill, "confidence")


def test_skill_has_no_progress_or_mastery_state() -> None:
    skill = make_skill()

    assert not hasattr(skill, "progress")
    assert not hasattr(skill, "mastery")
    assert not hasattr(skill, "current_level")
    assert not hasattr(skill, "proficiency")


# ---------------------------------------------------------------------------
# No hierarchy (FR-011 / DR-012)
# ---------------------------------------------------------------------------


def test_skill_does_not_require_a_hierarchy() -> None:
    skill = make_skill()

    assert not hasattr(skill, "parent_skill_id")
    assert not hasattr(skill, "child_skills")
    # The Skill model remains flat.
    assert isinstance(skill, Skill)


# ---------------------------------------------------------------------------
# No examination or curriculum ownership (FR-012 / FR-013 / DR-013 / DR-014)
# ---------------------------------------------------------------------------


def test_skill_has_no_examination_specific_state() -> None:
    skill = make_skill()

    assert not hasattr(skill, "exam_id")
    assert not hasattr(skill, "exam_type")
    assert not hasattr(skill, "nift_skill")
    assert not hasattr(skill, "nid_skill")
    assert not hasattr(skill, "ceed_skill")


def test_skill_has_no_curriculum_specific_state() -> None:
    skill = make_skill()

    assert not hasattr(skill, "curriculum")
    assert not hasattr(skill, "curriculum_id")


# ---------------------------------------------------------------------------
# No generation dependency (FR-014 / DR-015)
# ---------------------------------------------------------------------------


def test_skill_has_no_generation_dependency() -> None:
    skill = make_skill()

    assert not hasattr(skill, "provider")
    assert not hasattr(skill, "model")
    assert not hasattr(skill, "prompt")


# ---------------------------------------------------------------------------
# Minimal structure
# ---------------------------------------------------------------------------


def test_skill_has_only_minimal_fields() -> None:
    skill = make_skill()

    assert {field.name for field in fields(skill)} == {"id", "name", "description"}


# ---------------------------------------------------------------------------
# Domain boundaries (DR-016)
# ---------------------------------------------------------------------------


def test_skill_source_has_no_persistence_dependencies() -> None:
    for module in ("sqlalchemy", "psycopg", "redis", "sqlite3", "motor"):
        assert f"import {module}" not in SKILL_SOURCE
        assert f"from {module}" not in SKILL_SOURCE


def test_skill_source_has_no_framework_dependencies() -> None:
    for module in ("fastapi", "pydantic", "uvicorn"):
        assert f"import {module}" not in SKILL_SOURCE
        assert f"from {module}" not in SKILL_SOURCE


@pytest.mark.parametrize("forbidden", ["NIFT", "NID", "CEED"])
def test_skill_source_has_no_examination_specific_terminology(
    forbidden: str,
) -> None:
    assert forbidden.lower() not in SKILL_SOURCE.lower()


@pytest.mark.parametrize(
    "forbidden_identifier",
    [
        "current_level",
        "proficiency",
        "parent_skill_id",
        "child_skills",
        "exam_id",
        "exam_type",
        "nift_skill",
        "nid_skill",
        "ceed_skill",
        "curriculum_id",
        "score",
        "percentage",
        "grade",
        "confidence",
    ],
)
def test_skill_source_has_no_forbidden_state_identifiers(
    forbidden_identifier: str,
) -> None:
    assert forbidden_identifier not in SKILL_SOURCE


def test_skill_is_usable_in_memory_without_infrastructure() -> None:
    skill = make_skill()

    assert isinstance(skill, Skill)
    assert skill.name is not None
    assert skill.description is not None
