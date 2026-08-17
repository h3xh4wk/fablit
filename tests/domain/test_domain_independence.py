"""Domain independence tests (SPEC-005 through SPEC-011)."""

from __future__ import annotations

from pathlib import Path

import pytest

import fablit.domain
from fablit.domain import (
    ActivityType,
    AssessmentStatus,
)

from .helpers import make_activity, make_assessment

DOMAIN_SOURCE = list(Path(fablit.domain.__file__).parent.glob("*.py"))


def _domain_source_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in DOMAIN_SOURCE)


@pytest.mark.parametrize(
    "forbidden",
    ["NIFT", "NID", "CEED"],
)
def test_no_examination_specific_terminology_in_domain_code(forbidden: str) -> None:
    assert forbidden.lower() not in _domain_source_text().lower()


def test_domain_code_has_no_content_pack_references() -> None:
    source = _domain_source_text().lower()
    assert "content pack" not in source
    assert "content_pack" not in source


def test_domain_code_has_no_skill_lab_references() -> None:
    source = _domain_source_text().lower()
    assert "skill lab" not in source
    assert "skill_lab" not in source


def test_domain_code_has_no_persistence_dependencies() -> None:
    source = _domain_source_text()
    for module in ("sqlalchemy", "psycopg", "redis", "sqlite3", "motor"):
        assert f"import {module}" not in source
        assert f"from {module}" not in source


def test_domain_code_has_no_framework_dependencies() -> None:
    source = _domain_source_text()
    for module in ("fastapi", "pydantic", "uvicorn"):
        assert f"import {module}" not in source
        assert f"from {module}" not in source


def test_domain_implements_feedback_reflection_and_skill() -> None:
    source = _domain_source_text()
    # SPEC-008 introduces Feedback, SPEC-009 introduces Reflection as the
    # learner's response to that Feedback, and SPEC-010 introduces Skill as
    # the measurable, transferable capability being developed.
    assert "class Feedback" in source
    assert "class Reflection" in source
    assert "class Skill" in source


def test_domain_implements_stimulus_models() -> None:
    source = _domain_source_text()
    # SPEC-015 introduces the stimulus context an activity may define and the
    # resolved Stimulus Instance that is part of the learner's activity
    # instance (SPEC-015 §6, §15–16).
    assert "class ActivityStimulusContext" in source
    assert "class StimulusInstance" in source
    assert "class InvalidStimulusError" in source
    assert "class InvalidStimulusContextError" in source


def test_domain_has_no_skill_activity_relationship_entity() -> None:
    # SPEC-011 models the Skill-Activity association on the Assessment
    # Activity itself; it must not introduce a dedicated relationship entity.
    source = _domain_source_text()
    assert "class SkillAssociation" not in source
    assert "class SkillActivity" not in source
    assert "class SkillActivityRelationship" not in source


def test_same_model_works_for_design_education() -> None:
    assessment = make_assessment(
        title="Portfolio Review",
        description="A portfolio review for a design portfolio.",
        status=AssessmentStatus.DRAFT,
        activities=(
            make_activity(
                activity_type=ActivityType.OBSERVATION,
                instructions="Upload and annotate your best sketch.",
                position=0,
            ),
            make_activity(
                activity_type=ActivityType.REFLECTION,
                instructions="Reflect on your creative process.",
                position=1,
            ),
        ),
    )

    assert assessment.title == "Portfolio Review"
    assert len(assessment.activities) == 2


def test_same_model_works_for_communication_practice() -> None:
    assessment = make_assessment(
        title="Interview Practice",
        description="Practice for a job interview.",
        status=AssessmentStatus.PUBLISHED,
        activities=(
            make_activity(
                activity_type=ActivityType.WRITTEN_RESPONSE,
                instructions="Answer the interviewer's prompt in writing.",
                position=0,
            ),
        ),
    )

    assert assessment.title == "Interview Practice"
    assert assessment.ordered_activities()[0].position == 0


def test_same_model_works_for_research_methodology() -> None:
    assessment = make_assessment(
        title="Research Methods",
        description="A research methodology refresher.",
        status=AssessmentStatus.DRAFT,
        activities=(
            make_activity(
                activity_type=ActivityType.MULTIPLE_CHOICE,
                instructions="Choose the correct research method.",
                position=0,
            ),
            make_activity(
                activity_type=ActivityType.REFLECTION,
                instructions="Reflect on your research approach.",
                position=1,
            ),
        ),
    )

    assert len(assessment.activities) == 2


def test_activity_types_are_generic() -> None:
    assert {activity_type.value for activity_type in ActivityType} == {
        "multiple_choice",
        "written_response",
        "observation",
        "reflection",
    }
