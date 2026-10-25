"""Brief-drafting contract tests (SPEC-040 §6, §8).

The provider's structured draft is untrusted. These tests protect what the
authoring workflow relies on before anything reaches the form: field names and
controlled values from the existing brief schema, bounded text, and provenance
that keeps notes-grounded facts, AI suggestions, and assumptions distinct.
"""

from __future__ import annotations

import dataclasses
from typing import Any, cast

import pytest

from app.authoring import AuthoringBrief
from fablit.application import (
    BRIEF_FIELDS,
    BriefFieldSource,
    InvalidBriefDraftError,
    parse_brief_draft,
)


def _parse(payload: object) -> Any:
    """Call the parser with an intentionally untyped payload."""
    return parse_brief_draft(cast(Any, payload))


# --- Schema reuse -------------------------------------------------------------


def test_brief_fields_match_the_existing_authoring_form_schema() -> None:
    """SPEC-040 §6: drafting reuses the existing brief schema, not a copy."""
    assert tuple(field.name for field in dataclasses.fields(AuthoringBrief)) == (
        BRIEF_FIELDS
    )


# --- Parsing & provenance -----------------------------------------------------


def test_parsed_draft_keeps_values_and_their_sources() -> None:
    draft = _parse(
        {
            "fields": {
                "practice_area": {"value": "Visual analysis", "source": "notes"},
                "purpose": {
                    "value": "Distinguish evidence from interpretation.",
                    "source": "suggested",
                },
                "constraints": {
                    "value": "One paragraph.",
                    "source": "assumed",
                },
            },
            "assumptions": ["The learner group is Year 10."],
        }
    )

    assert draft.proposed_values() == {
        "practice_area": "Visual analysis",
        "purpose": "Distinguish evidence from interpretation.",
        "constraints": "One paragraph.",
    }
    assert draft.fields["practice_area"].source is BriefFieldSource.NOTES
    assert draft.fields["purpose"].source is BriefFieldSource.SUGGESTED
    assert draft.fields["constraints"].source is BriefFieldSource.ASSUMED
    assert draft.assumptions == ("The learner group is Year 10.",)
    assert draft.warnings == ()


def test_missing_or_unknown_provenance_is_read_as_a_suggestion() -> None:
    draft = _parse(
        {
            "fields": {
                "practice_area": "Visual analysis",
                "purpose": {"value": "Notice evidence.", "source": "certain"},
            }
        }
    )

    assert draft.fields["practice_area"].source is BriefFieldSource.SUGGESTED
    assert draft.fields["purpose"].source is BriefFieldSource.SUGGESTED


def test_unknown_fields_are_ignored_with_an_author_facing_warning() -> None:
    draft = _parse(
        {
            "fields": {
                "practice_area": {"value": "Visual analysis"},
                "score_target": {"value": "Grade 9"},
            }
        }
    )

    assert set(draft.fields) == {"practice_area"}
    assert any("score_target" in warning for warning in draft.warnings)


# --- Controlled values --------------------------------------------------------


def test_controlled_values_map_onto_the_existing_allowed_options() -> None:
    draft = _parse(
        {
            "fields": {
                "intended_mode": {"value": "Full Practice"},
                "primary_creative_thinking_lens": {"value": "observe"},
            }
        }
    )

    assert draft.fields["intended_mode"].value == "full-practice"
    assert draft.fields["primary_creative_thinking_lens"].value == "Observe"


def test_unsupported_controlled_value_is_refused_with_a_clear_reason() -> None:
    draft = _parse(
        {
            "fields": {
                "intended_mode": {"value": "lecture"},
                "practice_area": {"value": "Visual analysis"},
            }
        }
    )

    assert "intended_mode" not in draft.fields
    assert draft.fields["practice_area"].value == "Visual analysis"
    assert any(
        "Intended practice mode" in warning
        and "not one of the existing options" in warning
        for warning in draft.warnings
    )


# --- Boundaries ---------------------------------------------------------------


def test_oversized_field_is_refused_rather_than_written_into_the_form() -> None:
    draft = _parse(
        {
            "fields": {
                "practice_area": {"value": "x" * 2001},
                "purpose": {"value": "Notice evidence."},
            }
        }
    )

    assert "practice_area" not in draft.fields
    assert any("Practice area" in warning for warning in draft.warnings)


def test_blank_proposals_are_simply_not_offered() -> None:
    draft = _parse(
        {
            "fields": {
                "practice_area": {"value": "Visual analysis"},
                "continuation_intent": {"value": "   "},
            }
        }
    )

    assert "continuation_intent" not in draft.fields
    assert draft.warnings == ()


def test_assumptions_are_bounded_and_tidied() -> None:
    long_assumption = "a" * 500
    draft = _parse(
        {
            "fields": {"practice_area": {"value": "Visual analysis"}},
            "assumptions": [
                "  ",
                "The learner group is Year 10.",
                long_assumption,
                *[f"Assumption {index}" for index in range(10)],
                42,
            ],
        }
    )

    assert len(draft.assumptions) == 6
    assert draft.assumptions[0] == "The learner group is Year 10."
    assert len(draft.assumptions[1]) == 300
    assert draft.assumptions[1].endswith("…")


# --- Examination context (AC-5) -----------------------------------------------


def test_examination_context_is_never_presented_as_a_fact() -> None:
    draft = _parse(
        {
            "fields": {
                "examination_context": {
                    "value": "A two-hour official past paper.",
                    "source": "notes",
                }
            }
        }
    )

    proposal = draft.fields["examination_context"]
    assert proposal.value == "A two-hour official past paper."
    assert proposal.source is BriefFieldSource.ASSUMED
    assert any("Examination context" in warning for warning in draft.warnings)


# --- Malformed output ---------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "fields",
        {},
        {"fields": []},
        {"fields": {}},
        {"fields": {"practice_area": 42}},
        {"fields": {"practice_area": {"value": None}}},
    ],
)
def test_unusable_payloads_are_refused(payload: object) -> None:
    with pytest.raises(InvalidBriefDraftError):
        _parse(payload)
