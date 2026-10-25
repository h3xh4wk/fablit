"""AI-assisted authoring brief drafting (SPEC-040).

SPEC-040 lets an authorised author turn rough notes, pasted source text, or a
short topic description into an editable draft of the *existing* SPEC-032
authoring brief. This module owns the provider-neutral, server-side part of
that operation:

- the brief field list and labels, taken from the existing brief schema (no
  parallel brief model is introduced);
- the source labels that keep notes-grounded facts, AI suggestions, and
  assumptions that need confirmation distinguishable while the author reviews
  the draft;
- bounded input and output limits; and
- :func:`parse_brief_draft`, which turns an untrusted provider mapping into a
  validated :class:`BriefDraft` or raises :class:`InvalidBriefDraftError`.

Nothing here persists anything: a draft is rendered straight back into the
existing editable form, and candidate generation, approval, and publication
stay the separate explicit actions they already were.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

from .demo_data import PRACTICE_CAPABILITIES
from .errors import InvalidBriefDraftError
from .practice_modes import PracticeMode

#: Maximum characters accepted from the author's notes or pasted source text.
MAX_NOTES_CHARS: Final[int] = 8000

#: Maximum characters accepted in one proposed brief field.
MAX_FIELD_CHARS: Final[int] = 2000

#: Maximum number of assumptions shown for a single draft.
MAX_ASSUMPTIONS: Final[int] = 6

#: Maximum characters accepted in one assumption.
MAX_ASSUMPTION_CHARS: Final[int] = 300

#: The existing SPEC-032 brief's required fields, in form order.
REQUIRED_BRIEF_FIELDS: Final[tuple[str, ...]] = (
    "practice_area",
    "learner_context",
    "purpose",
    "intended_mode",
    "response_form",
    "evaluation_intent",
    "feedback_intent",
    "reflection_intent",
)

#: The existing SPEC-032 brief's optional fields, in form order.
OPTIONAL_BRIEF_FIELDS: Final[tuple[str, ...]] = (
    "examination_context",
    "primary_creative_thinking_lens",
    "constraints",
    "stimulus_requirements",
    "continuation_intent",
)

#: Every field of the existing authoring brief, required first.
BRIEF_FIELDS: Final[tuple[str, ...]] = REQUIRED_BRIEF_FIELDS + OPTIONAL_BRIEF_FIELDS

#: Author-facing names used in draft status messages and provenance labels.
FIELD_LABELS: Final[dict[str, str]] = {
    "practice_area": "Practice area",
    "learner_context": "Intended learner context",
    "purpose": "Practice purpose",
    "intended_mode": "Intended practice mode",
    "response_form": "Desired response form",
    "evaluation_intent": "Evaluation intent",
    "feedback_intent": "Feedback intent",
    "reflection_intent": "Reflection intent",
    "examination_context": "Examination context",
    "primary_creative_thinking_lens": "Primary thinking lens",
    "constraints": "Constraints",
    "stimulus_requirements": "Stimulus or context requirements",
    "continuation_intent": "Continuation intent",
}

#: Controlled fields reuse the existing allowed options (SPEC-040 §6).
CONTROLLED_FIELD_VALUES: Final[dict[str, tuple[str, ...]]] = {
    "intended_mode": tuple(mode.value for mode in PracticeMode),
    "primary_creative_thinking_lens": PRACTICE_CAPABILITIES,
}


class BriefFieldSource(StrEnum):
    """Where a proposed field value came from (SPEC-040 §5).

    The three sources are the distinction the review form has to make
    visible: a fact stated in the author's notes, an instructional choice the
    AI proposed, and an assumption the author must confirm before continuing.
    """

    NOTES = "notes"
    SUGGESTED = "suggested"
    ASSUMED = "assumed"


#: Author-facing label for each provenance source.
SOURCE_LABELS: Final[dict[BriefFieldSource, str]] = {
    BriefFieldSource.NOTES: "From your notes",
    BriefFieldSource.SUGGESTED: "AI suggestion",
    BriefFieldSource.ASSUMED: "Assumption to confirm",
}

#: Shown beside examination context: Fablit never presents AI output as
#: official examination guidance (SPEC-040 §4, AC-5).
EXAMINATION_CONTEXT_DETAIL: Final[str] = (
    "Fablit cannot confirm official examination or institutional requirements. "
    "Check this against your own sources before you continue."
)


@dataclass(frozen=True)
class BriefFieldProposal:
    """One proposed value for one brief field, with its provenance."""

    value: str
    source: BriefFieldSource = BriefFieldSource.SUGGESTED

    def __post_init__(self) -> None:
        """Reject blank or oversized proposals and unknown provenance."""
        if not isinstance(self.value, str) or not self.value.strip():
            raise InvalidBriefDraftError(
                f"a drafted brief field must be non-blank text, got {self.value!r}"
            )
        if len(self.value) > MAX_FIELD_CHARS:
            raise InvalidBriefDraftError(
                "a drafted brief field is longer than the supported "
                f"{MAX_FIELD_CHARS} characters"
            )
        if not isinstance(self.source, BriefFieldSource):
            raise InvalidBriefDraftError(
                f"unsupported draft field source: {self.source!r}"
            )


@dataclass(frozen=True)
class BriefDraft:
    """Validated, provider-neutral draft of an authoring brief (SPEC-040 §4).

    ``fields`` only contains what the provider actually proposed. The caller
    merges those proposals into the form it already has, so a draft never
    blanks out a field or discards the author's edits by omission.
    """

    fields: Mapping[str, BriefFieldProposal]
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Reject an empty draft or a proposal for an unknown brief field."""
        if not self.fields:
            raise InvalidBriefDraftError(
                "a drafted brief must propose at least one field"
            )
        for name, proposal in self.fields.items():
            if name not in BRIEF_FIELDS:
                raise InvalidBriefDraftError(
                    f"unsupported brief field in draft: {name!r}"
                )
            if not isinstance(proposal, BriefFieldProposal):
                raise InvalidBriefDraftError(
                    f"draft field {name!r} must be a BriefFieldProposal"
                )

    def proposed_values(self) -> dict[str, str]:
        """Return the proposed text keyed by brief field name."""
        return {name: proposal.value for name, proposal in self.fields.items()}


def _normalise(choice: str) -> str:
    """Fold a controlled value into a comparable form (``Full Practice``)."""
    return re.sub(r"[^a-z0-9]+", "-", choice.strip().lower()).strip("-")


def _controlled_value(name: str, value: str) -> str | None:
    """Map a proposal onto an existing allowed value, or return ``None``.

    SPEC-040 §6: AI output outside the allowed values must never introduce a
    new enum value. Case and spacing differences are mapped; anything else is
    refused so the existing option stays in place.
    """
    allowed = CONTROLLED_FIELD_VALUES.get(name)
    if allowed is None:
        return value
    folded = _normalise(value)
    for option in allowed:
        if _normalise(option) == folded:
            return option
    return None


def _parse_proposal(
    name: str, raw: object
) -> tuple[BriefFieldProposal | None, str | None]:
    """Parse one provider field proposal into a validated value.

    Returns the proposal (or ``None`` when it must be refused) plus a warning
    that explains a refused or adjusted value to the author.
    """
    label = FIELD_LABELS.get(name, name)
    raw_value: object
    raw_source: object
    if isinstance(raw, str):
        raw_value, raw_source = raw, "suggested"
    elif isinstance(raw, Mapping):
        raw_value = raw.get("value")
        raw_source = raw.get("source")
    else:
        return None, f"“{label}” was left unchanged: the draft value was not text."

    if not isinstance(raw_value, str):
        return None, f"“{label}” was left unchanged: the draft value was not text."
    value = raw_value.strip()
    if not value:
        # A blank proposal is not an error: optional fields may stay empty.
        return None, None
    if len(value) > MAX_FIELD_CHARS:
        return None, (
            f"“{label}” was left unchanged: the draft value was longer than "
            f"{MAX_FIELD_CHARS} characters."
        )

    # An unknown or missing provenance is safest read as an AI suggestion:
    # nothing is ever presented as author-supplied fact by default.
    source = BriefFieldSource.SUGGESTED
    if isinstance(raw_source, str):
        try:
            source = BriefFieldSource(raw_source.strip().lower())
        except ValueError:
            source = BriefFieldSource.SUGGESTED

    mapped = _controlled_value(name, value)
    if mapped is None:
        options = ", ".join(CONTROLLED_FIELD_VALUES[name])
        return None, (
            f"“{label}” was left unchanged: the suggestion {value!r} is not "
            f"one of the existing options ({options})."
        )

    if name == "examination_context":
        # AC-5: no generated examination detail is presented as fact.
        return (
            BriefFieldProposal(value=mapped, source=BriefFieldSource.ASSUMED),
            (
                "“Examination context” is marked as an assumption to confirm: "
                "Fablit does not verify official examination requirements."
            ),
        )

    return BriefFieldProposal(value=mapped, source=source), None


def _parse_assumptions(raw: object) -> tuple[str, ...]:
    """Bound and clean the provider's list of assumptions (SPEC-040 §8)."""
    if not isinstance(raw, list | tuple):
        return ()
    assumptions: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text:
            continue
        if len(text) > MAX_ASSUMPTION_CHARS:
            text = text[: MAX_ASSUMPTION_CHARS - 1].rstrip() + "…"
        assumptions.append(text)
        if len(assumptions) >= MAX_ASSUMPTIONS:
            break
    return tuple(assumptions)


def parse_brief_draft(payload: Mapping[str, Any]) -> BriefDraft:
    """Validate an untrusted provider payload as a brief draft (SPEC-040 §8).

    The expected shape is ``{"fields": {name: {"value", "source"}},
    "assumptions": [...]}``. Unknown fields, out-of-range controlled values,
    and oversized or non-text proposals are refused with an author-facing
    warning instead of being written into the form; malformed payloads raise
    :class:`InvalidBriefDraftError` so the workflow can preserve the author's
    work and offer a retry.
    """
    if not isinstance(payload, Mapping):
        raise InvalidBriefDraftError("the drafted brief must be a mapping")

    raw_fields = payload.get("fields")
    if not isinstance(raw_fields, Mapping) or not raw_fields:
        raise InvalidBriefDraftError("the drafted brief must contain a 'fields' object")

    proposals: dict[str, BriefFieldProposal] = {}
    warnings: list[str] = []
    for raw_name, raw_proposal in raw_fields.items():
        name = str(raw_name).strip()
        if name not in BRIEF_FIELDS:
            warnings.append(f"Ignored an unrecognised brief field: {name!r}.")
            continue
        proposal, warning = _parse_proposal(name, raw_proposal)
        if warning:
            warnings.append(warning)
        if proposal is not None:
            proposals[name] = proposal

    return BriefDraft(
        fields=proposals,
        assumptions=_parse_assumptions(payload.get("assumptions")),
        warnings=tuple(warnings),
    )


__all__ = [
    "BRIEF_FIELDS",
    "CONTROLLED_FIELD_VALUES",
    "EXAMINATION_CONTEXT_DETAIL",
    "FIELD_LABELS",
    "MAX_ASSUMPTIONS",
    "MAX_ASSUMPTION_CHARS",
    "MAX_FIELD_CHARS",
    "MAX_NOTES_CHARS",
    "OPTIONAL_BRIEF_FIELDS",
    "REQUIRED_BRIEF_FIELDS",
    "SOURCE_LABELS",
    "BriefDraft",
    "BriefFieldProposal",
    "BriefFieldSource",
    "parse_brief_draft",
]
