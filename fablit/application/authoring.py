"""AI-assisted practice authoring workflow (SPEC-032).

SPEC-032 lets an authorized internal author use AI to draft *candidate*
practice activities while keeping the curated library human-reviewed. This
module owns the smallest representation the current workflow needs:

- :class:`PracticeAuthoringBrief` — the structured description of the
  practice an author wants.
- :class:`PracticeCandidate` — a structured, SPEC-029-compatible candidate
  plus its authoring provenance.
- :func:`validate_candidate` — the structural (SPEC-029) and feedback
  (SPEC-030) gate that decides whether a candidate may enter review.
- :class:`AuthoringCandidateStore` — the authoring workflow state, keeping
  approved content separate from unapproved candidates.

None of this is a learning-domain concept: authoring states are workflow
states, never learner progress, and the module never touches the learner
journey. AI proposes candidates; the human decides what enters the library
(AA-001). Generation is provider-agnostic: the workflow works with no AI
provider configured (a deterministic, brief-derived draft) so authoring and
learner practice never depend on AI availability (SPEC-032 §17).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from .demo_data import PRACTICE_CAPABILITIES
from .errors import (
    CandidateNotApprovableError,
    CandidateNotFoundError,
    InvalidAuthoringBriefError,
)
from .practice_modes import PracticeMode
from .store import PracticeContentContract

#: Feedback/evaluation language SPEC-030 forbids in generated guidance
#: (§6): grades, inferred ability/motivation/effort, mastery, rankings, and
#: learner labels. Word-boundary matched, case-insensitive.
FORBIDDEN_FEEDBACK_TERMS: tuple[str, ...] = (
    "grade",
    "grading",
    "score",
    "scoring",
    "mastery",
    "streak",
    "ranking",
    "leaderboard",
    "ability",
    "motivation",
    "effort",
    "prediction",
    "predict",
    "learner label",
)

#: The provider-agnostic provenance label used when no AI provider is
#: configured and the authoring workflow derives a draft from the brief.
DETERMINISTIC_PROVIDER = "fablit-deterministic"
DETERMINISTIC_MODEL = "brief-derived"


class CandidateStatus(StrEnum):
    """Authoring workflow states for a practice candidate (SPEC-032 §9).

    These are *authoring* states, not learner progress. ``GENERATED`` keeps
    the wire value ``"candidate"`` established by the SEC-001 boundary: a
    freshly generated candidate is a candidate until a human approves it.
    """

    DRAFT = "draft"
    GENERATED = "candidate"
    VALIDATED = "validated"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


@dataclass(frozen=True)
class PracticeAuthoringBrief:
    """A structured description of the practice an author wants (SPEC-032 §4).

    The brief describes educational intent — purpose, task, thinking demand,
    response form — rather than merely naming an exam. That is what keeps an
    exam name from standing in for authoring instructions (AA-006): the
    required intent fields cannot be satisfied by an exam label alone.
    """

    practice_area: str
    practice_purpose: str
    task: str
    response_form: str
    primary_capability: str
    practice_mode: PracticeMode
    learner_context: str = ""
    expected_thinking: str = ""
    evaluation_intent: str = ""
    feedback_intent: str = ""
    reflection_intent: str = ""
    continuation_intent: str = ""
    examination_context: str | None = None
    secondary_capability: str | None = None
    stimulus_requirements: str = ""
    constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("practice_area", "practice_purpose", "task", "response_form"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidAuthoringBriefError(
                    f"authoring brief field {name!r} must be non-blank text, "
                    f"got {value!r}"
                )
        if not isinstance(self.practice_mode, PracticeMode):
            raise InvalidAuthoringBriefError(
                "authoring brief must declare a supported practice mode "
                f"(got {self.practice_mode!r}); choose from "
                f"{', '.join(sorted(mode.value for mode in PracticeMode))}"
            )
        if self.primary_capability not in PRACTICE_CAPABILITIES:
            raise InvalidAuthoringBriefError(
                "authoring brief primary capability must be a supported "
                f"practice capability (got {self.primary_capability!r}); "
                f"choose from {', '.join(PRACTICE_CAPABILITIES)}"
            )
        if (
            self.secondary_capability is not None
            and self.secondary_capability not in PRACTICE_CAPABILITIES
        ):
            raise InvalidAuthoringBriefError(
                "authoring brief secondary capability must be a supported "
                f"practice capability (got {self.secondary_capability!r}); "
                f"choose from {', '.join(PRACTICE_CAPABILITIES)}"
            )
        if self.secondary_capability == self.primary_capability:
            raise InvalidAuthoringBriefError(
                "authoring brief secondary capability must differ from the "
                f"primary capability (got {self.secondary_capability!r})"
            )
        if not isinstance(self.constraints, tuple):
            raise InvalidAuthoringBriefError(
                "authoring brief constraints must be provided as a tuple "
                f"(got {self.constraints!r})"
            )
        for constraint in self.constraints:
            if not isinstance(constraint, str) or not constraint.strip():
                raise InvalidAuthoringBriefError(
                    "authoring brief constraints must be non-blank text "
                    f"(got {self.constraints!r})"
                )

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe view of the brief for provenance/response."""
        return {
            "practice_area": self.practice_area,
            "practice_purpose": self.practice_purpose,
            "task": self.task,
            "response_form": self.response_form,
            "primary_capability": self.primary_capability,
            "practice_mode": self.practice_mode.value,
            "learner_context": self.learner_context,
            "expected_thinking": self.expected_thinking,
            "evaluation_intent": self.evaluation_intent,
            "feedback_intent": self.feedback_intent,
            "reflection_intent": self.reflection_intent,
            "continuation_intent": self.continuation_intent,
            "examination_context": self.examination_context,
            "secondary_capability": self.secondary_capability,
            "stimulus_requirements": self.stimulus_requirements,
            "constraints": list(self.constraints),
        }


@dataclass(frozen=True)
class AuthoringRevision:
    """A superseded version of a candidate, kept for traceability (§10)."""

    version: int
    title: str
    description: str
    contract: PracticeContentContract | None
    edited_at: datetime
    editor: str | None = None


@dataclass(frozen=True)
class AuthoringProvenance:
    """Authoring source retained for approved content (SPEC-032 §10).

    Provenance stays internal: it describes how a candidate was drafted and
    who decided its outcome. It is never exposed to ordinary learners.
    """

    brief: PracticeAuthoringBrief
    generated_at: datetime
    provider: str
    model: str
    version: int = 1
    reviewer: str | None = None
    decided_at: datetime | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.generated_at, datetime)
            or self.generated_at.tzinfo is None
        ):
            raise InvalidAuthoringBriefError(
                "authoring provenance requires a timezone-aware generation "
                f"time (got {self.generated_at!r})"
            )
        for name in ("provider", "model"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidAuthoringBriefError(
                    f"authoring provenance {name!r} must be non-blank text, "
                    f"got {value!r}"
                )
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise InvalidAuthoringBriefError(
                "authoring provenance version must be an integer "
                f"(got {self.version!r})"
            )
        if self.version < 1:
            raise InvalidAuthoringBriefError(
                f"authoring provenance version must be at least 1 (got {self.version})"
            )


@dataclass(frozen=True)
class CandidateValidation:
    """The result of validating a candidate (SPEC-032 §7).

    ``structural_errors`` are SPEC-029 contract gaps that block approval;
    ``feedback_errors`` are SPEC-030 violations that also block approval;
    ``content_warnings`` are review aids that inform, but never auto-approve
    or auto-reject, the reviewer.
    """

    structural_errors: tuple[str, ...] = ()
    feedback_errors: tuple[str, ...] = ()
    content_warnings: tuple[str, ...] = ()

    @property
    def is_approvable(self) -> bool:
        """Whether a human may approve this candidate for the library."""
        return not self.structural_errors and not self.feedback_errors


@dataclass(frozen=True)
class PracticeCandidate:
    """A structured, reviewable practice candidate (SPEC-032 §5, §9).

    The candidate reuses the existing SPEC-029
    :class:`~fablit.application.store.PracticeContentContract` rather than a
    parallel learner-facing model. ``contract`` is ``None`` only when
    generated output was too incomplete to form one — which is itself a
    structural error that keeps the candidate out of the approval path.
    """

    brief: PracticeAuthoringBrief
    provenance: AuthoringProvenance
    title: str
    description: str
    contract: PracticeContentContract | None
    id: UUID = field(default_factory=uuid4)
    status: CandidateStatus = CandidateStatus.GENERATED
    validation: CandidateValidation = field(default_factory=CandidateValidation)
    revision: int = 1
    reviewer: str | None = None
    decided_at: datetime | None = None
    history: tuple[AuthoringRevision, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise InvalidAuthoringBriefError(
                f"practice candidate must have a valid identity (got {self.id!r})"
            )
        if not isinstance(self.status, CandidateStatus):
            raise InvalidAuthoringBriefError(
                f"practice candidate must declare a valid status (got {self.status!r})"
            )
        if not isinstance(self.revision, int) or self.revision < 1:
            raise InvalidAuthoringBriefError(
                "practice candidate revision must be at least 1 "
                f"(got {self.revision!r})"
            )

    @property
    def is_approved(self) -> bool:
        """Whether this candidate has been approved into the curated library."""
        return self.status is CandidateStatus.APPROVED

    @property
    def stimulus(self) -> None:
        """Application-layer candidates do not carry a stimulus image yet."""
        return None

    @property
    def supports_sketch_upload(self) -> bool:
        """Application-layer candidates do not opt into sketch evidence."""
        return False


def _derive_expected_thinking(brief: PracticeAuthoringBrief) -> str:
    if brief.expected_thinking.strip():
        return brief.expected_thinking.strip()
    capability = brief.primary_capability.lower()
    return (
        f"The learner uses {capability} thinking to move from the task toward "
        "a reasoned, evidence-based response rather than a vague summary."
    )


def _derive_contract(brief: PracticeAuthoringBrief) -> PracticeContentContract:
    """Build the SPEC-029 contract implied by a brief.

    Missing intent fields fall back to generic-but-relevant guidance so an
    author can still draft without filling every field; the reviewer sees
    the resulting contract in full before approving.
    """
    capability = brief.primary_capability.lower()
    return PracticeContentContract(
        purpose=brief.practice_purpose.strip(),
        task=brief.task.strip(),
        expected_thinking=_derive_expected_thinking(brief),
        response_contract=brief.response_form.strip(),
        evaluation_intent=brief.evaluation_intent.strip()
        or f"Look for specific {capability} thinking grounded in the response.",
        feedback_intent=brief.feedback_intent.strip()
        or (
            "Name one concrete strength, explain why it matters, and point to "
            "one useful next move."
        ),
        reflection_intent=brief.reflection_intent.strip()
        or (
            "Invite the learner to notice how they approached the task and "
            "what they would change in a future attempt."
        ),
        continuation_intent=brief.continuation_intent.strip()
        or "Continue with a related practice that extends the same thinking move.",
    )


def _derive_title(brief: PracticeAuthoringBrief) -> str:
    return f"{brief.practice_area.strip()} — {brief.primary_capability} Practice"


def _derive_description(brief: PracticeAuthoringBrief) -> str:
    return brief.learner_context.strip() or brief.practice_purpose.strip()


def draft_candidate_from_brief(
    brief: PracticeAuthoringBrief,
    *,
    generated_at: datetime | None = None,
    provider: str = DETERMINISTIC_PROVIDER,
    model: str = DETERMINISTIC_MODEL,
    reviewer: str | None = None,
) -> PracticeCandidate:
    """Derive a structured candidate directly from the brief (no AI needed).

    This is the provider-free path: authoring still works when no AI provider
    is configured, so AI availability never blocks content creation
    (SPEC-032 §17). The candidate is validated before it is returned.
    """
    generated_at = generated_at or datetime.now(UTC)
    candidate = PracticeCandidate(
        brief=brief,
        title=_derive_title(brief),
        description=_derive_description(brief),
        contract=_derive_contract(brief),
        provenance=AuthoringProvenance(
            brief=brief,
            generated_at=generated_at,
            provider=provider,
            model=model,
            reviewer=reviewer,
        ),
    )
    return with_validation(candidate)


def candidate_from_provider_output(
    output: Mapping[str, Any],
    brief: PracticeAuthoringBrief,
    *,
    provider: str,
    model: str,
    generated_at: datetime | None = None,
) -> PracticeCandidate:
    """Turn a provider's structured output into a candidate (SPEC-032 §5).

    The expected provider shape is ``{"title", "description", "contract"}``
    where ``contract`` carries the SPEC-029 fields. Parsing is deliberately
    tolerant: malformed or incomplete output becomes a candidate with
    structural errors rather than entering the approval path (§17).
    """
    generated_at = generated_at or datetime.now(UTC)

    title = _first_text(output.get("title"))
    description = _first_text(output.get("description"))
    activity = output.get("activity")
    if isinstance(activity, Mapping):
        title = title or _first_text(activity.get("title"))
        description = description or _first_text(activity.get("instructions"))

    contract_data = output.get("contract")
    if not isinstance(contract_data, Mapping):
        contract_data = output
    contract = _contract_from_mapping(contract_data)

    candidate = PracticeCandidate(
        brief=brief,
        title=title,
        description=description,
        contract=contract,
        provenance=AuthoringProvenance(
            brief=brief,
            generated_at=generated_at,
            provider=provider,
            model=model,
        ),
    )
    return with_validation(candidate)


def _first_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


_CONTRACT_FIELDS: tuple[str, ...] = (
    "purpose",
    "task",
    "expected_thinking",
    "response_contract",
    "evaluation_intent",
    "feedback_intent",
    "reflection_intent",
    "continuation_intent",
)


def _contract_from_mapping(data: Mapping[str, Any]) -> PracticeContentContract | None:
    """Build a SPEC-029 contract from a mapping, or ``None`` when incomplete.

    A blank field is never silently accepted: an incomplete contract cannot
    be represented, so the candidate is flagged structurally invalid instead
    (SPEC-032 §7).
    """
    values: dict[str, str] = {}
    for name in _CONTRACT_FIELDS:
        raw = data.get(name)
        if not isinstance(raw, str) or not raw.strip():
            return None
        values[name] = raw.strip()
    try:
        return PracticeContentContract(**values)
    except Exception:  # noqa: BLE001 - any invalid contract is not approvable
        return None


def _feedback_language_errors(
    contract: PracticeContentContract | None,
) -> tuple[str, ...]:
    if contract is None:
        return ()
    text = f"{contract.feedback_intent} {contract.evaluation_intent}".lower()
    errors: list[str] = []
    for term in FORBIDDEN_FEEDBACK_TERMS:
        if _contains_term(text, term):
            errors.append(
                f"evaluation/feedback guidance must not use {term!r} (SPEC-030 §6)"
            )
    return tuple(errors)


def _contains_term(text: str, term: str) -> bool:
    """Whole-word match so 'grade' does not match 'upgrade'."""
    start = 0
    while (index := text.find(term, start)) != -1:
        before = text[index - 1] if index > 0 else " "
        after_index = index + len(term)
        after = text[after_index] if after_index < len(text) else " "
        if not before.isalnum() and not after.isalnum():
            return True
        start = index + 1
    return False


def validate_candidate(candidate: Any) -> CandidateValidation:
    """Validate a candidate against SPEC-029 (structure) and SPEC-030 (§7)."""
    structural: list[str] = []
    warnings: list[str] = []

    title = getattr(candidate, "title", None)
    if not isinstance(title, str) or not title.strip():
        data = getattr(candidate, "candidate_data", None)
        if isinstance(data, Mapping):
            title = data.get("title")
    title_str = str(title).strip() if isinstance(title, str) else ""
    if not title_str:
        structural.append("candidate is missing a learner-facing title")

    description = getattr(candidate, "description", None)
    if not isinstance(description, str) or not description.strip():
        data = getattr(candidate, "candidate_data", None)
        if isinstance(data, Mapping):
            description = data.get("description")
    desc_str = str(description).strip() if isinstance(description, str) else ""
    if not desc_str:
        structural.append("candidate is missing a learner-facing description")

    contract = getattr(candidate, "contract", None)
    contract_data: Mapping[str, Any] | None = None
    if isinstance(contract, PracticeContentContract):
        for name in _CONTRACT_FIELDS:
            val = getattr(contract, name, None)
            if not isinstance(val, str) or not val.strip():
                structural.append(
                    f"candidate content contract field {name!r} must be non-blank"
                )
    else:
        data = getattr(candidate, "candidate_data", None)
        raw_contract = data.get("contract") if isinstance(data, Mapping) else None
        if isinstance(raw_contract, Mapping):
            contract_data = raw_contract
            for name in _CONTRACT_FIELDS:
                val = raw_contract.get(name)
                if not isinstance(val, str) or not str(val).strip():
                    structural.append(
                        f"candidate content contract field {name!r} must be non-blank"
                    )
            if not structural:
                contract = _contract_from_mapping(raw_contract)
        elif raw_contract is not None:
            structural.append(
                f"candidate contract must be a mapping, got "
                f"{type(raw_contract).__name__}"
            )
        else:
            structural.append(
                "candidate does not provide a complete SPEC-029 practice "
                "content contract"
            )

    feedback_text = ""
    evaluation_text = ""
    if contract is not None:
        feedback_text = contract.feedback_intent
        evaluation_text = contract.evaluation_intent
    elif contract_data is not None:
        raw_fb = contract_data.get("feedback_intent")
        raw_ev = contract_data.get("evaluation_intent")
        feedback_text = str(raw_fb) if raw_fb is not None else ""
        evaluation_text = str(raw_ev) if raw_ev is not None else ""

    feedback_errors: list[str] = []
    text = f"{feedback_text} {evaluation_text}".lower()
    for term in FORBIDDEN_FEEDBACK_TERMS:
        if _contains_term(text, term):
            feedback_errors.append(
                f"evaluation/feedback guidance must not use {term!r} (SPEC-030 §6)"
            )

    brief = getattr(candidate, "brief", None)
    if brief:
        exam_context = getattr(brief, "examination_context", None)
        if exam_context and isinstance(exam_context, str) and exam_context.strip():
            purpose = ""
            if contract is not None:
                purpose = contract.purpose
            elif contract_data is not None:
                purpose = str(contract_data.get("purpose", ""))
            if purpose.strip().lower() == exam_context.strip().lower():
                warnings.append(
                    "exam name alone is not sufficient; explain the thinking the "
                    "exam context demands"
                )

        practice_area = getattr(brief, "practice_area", None)
        if practice_area and isinstance(practice_area, str) and practice_area.strip():
            area = practice_area.strip().lower()
            purpose = (
                contract.purpose.lower()
                if contract
                else (
                    str(contract_data.get("purpose", "")).lower()
                    if contract_data
                    else ""
                )
            )
            haystack = " ".join(
                filter(
                    None,
                    [
                        title_str.lower(),
                        desc_str.lower(),
                        purpose,
                    ],
                )
            )
            if area and area not in haystack:
                warnings.append(
                    "candidate does not reference the requested practice area "
                    f"{brief.practice_area!r}"
                )

        data = getattr(candidate, "candidate_data", None)
        if isinstance(data, Mapping):
            candidate_mode = (
                data.get("intended_mode")
                or data.get("mode")
                or data.get("practice_mode")
            )
            if candidate_mode:
                if candidate_mode not in ("short-drill", "full-practice"):
                    structural.append(
                        f"candidate declares an unsupported practice mode: "
                        f"{candidate_mode!r}"
                    )
                else:
                    brief_mode = getattr(brief, "intended_mode", None) or getattr(
                        brief, "practice_mode", None
                    )
                    if brief_mode:
                        brief_mode_val = (
                            brief_mode.value
                            if hasattr(brief_mode, "value")
                            else str(brief_mode)
                        )
                        if candidate_mode != brief_mode_val:
                            structural.append(
                                f"candidate practice mode {candidate_mode!r} "
                                f"does not match brief intended mode "
                                f"{brief_mode_val!r}"
                            )

            candidate_lens = data.get("primary_creative_thinking_lens") or data.get(
                "primary_capability"
            )
            if candidate_lens:
                if candidate_lens not in PRACTICE_CAPABILITIES:
                    structural.append(
                        "candidate declares an unsupported "
                        f"creative-thinking lens: {candidate_lens!r}"
                    )
                else:
                    brief_lens = getattr(
                        brief, "primary_creative_thinking_lens", None
                    ) or getattr(brief, "primary_capability", None)
                    if brief_lens and candidate_lens != brief_lens:
                        structural.append(
                            f"candidate thinking lens {candidate_lens!r} "
                            f"does not match brief lens {brief_lens!r}"
                        )

    return CandidateValidation(
        structural_errors=tuple(structural),
        feedback_errors=tuple(feedback_errors),
        content_warnings=tuple(warnings),
    )


def with_validation(candidate: PracticeCandidate) -> PracticeCandidate:
    """Return the candidate with its current validation result attached."""
    return replace(candidate, validation=validate_candidate(candidate))


def serialize_candidate(candidate: PracticeCandidate) -> dict[str, Any]:
    """Return a JSON-safe view of a candidate for the authoring API."""
    contract = candidate.contract
    return {
        "id": str(candidate.id),
        "status": candidate.status.value,
        "title": candidate.title,
        "description": candidate.description,
        "revision": candidate.revision,
        "reviewer": candidate.reviewer,
        "is_approved": candidate.is_approved,
        "contract": (
            {
                "purpose": contract.purpose,
                "task": contract.task,
                "expected_thinking": contract.expected_thinking,
                "response_contract": contract.response_contract,
                "evaluation_intent": contract.evaluation_intent,
                "feedback_intent": contract.feedback_intent,
                "reflection_intent": contract.reflection_intent,
                "continuation_intent": contract.continuation_intent,
            }
            if contract is not None
            else None
        ),
        "validation": {
            "structural_errors": list(candidate.validation.structural_errors),
            "feedback_errors": list(candidate.validation.feedback_errors),
            "content_warnings": list(candidate.validation.content_warnings),
            "is_approvable": candidate.validation.is_approvable,
        },
        "provenance": {
            "provider": candidate.provenance.provider,
            "model": candidate.provenance.model,
            "generated_at": candidate.provenance.generated_at.isoformat(),
            "version": candidate.provenance.version,
            "reviewer": candidate.provenance.reviewer,
            "decided_at": (
                candidate.provenance.decided_at.isoformat()
                if candidate.provenance.decided_at is not None
                else None
            ),
            "brief": candidate.brief.as_dict(),
        },
    }


class AuthoringCandidateStore:
    """In-memory authoring workflow state (SPEC-032 §9-§11).

    Candidates are kept distinct from approved content, so only explicitly
    approved candidates are ever exposed as library content (AA-008). The
    store performs no persistence and no AI calls; it is the minimal
    representation the current workflow needs.
    """

    def __init__(self) -> None:
        self._candidates: dict[UUID, PracticeCandidate] = {}
        self._order: list[UUID] = []

    def add(self, candidate: PracticeCandidate) -> PracticeCandidate:
        """Record a candidate, attaching validation and duplicate warnings."""
        stored = with_validation(candidate)
        warnings = list(stored.validation.content_warnings)
        duplicate = self._duplicate_title(stored)
        if duplicate is not None:
            warnings.append(f"possible duplicate of existing candidate {duplicate!r}")
        if tuple(warnings) != stored.validation.content_warnings:
            stored = replace(
                stored,
                validation=replace(stored.validation, content_warnings=tuple(warnings)),
            )
        if candidate.id not in self._candidates:
            self._order.append(candidate.id)
        self._candidates[candidate.id] = stored
        return stored

    def _duplicate_title(self, candidate: PracticeCandidate) -> str | None:
        title = candidate.title.strip().lower()
        if not title:
            return None
        for existing in self._candidates.values():
            if existing.id != candidate.id and existing.title.strip().lower() == title:
                return existing.title
        return None

    def get(self, candidate_id: UUID) -> PracticeCandidate:
        try:
            return self._candidates[candidate_id]
        except KeyError:
            raise CandidateNotFoundError(
                f"authoring candidate {candidate_id} was not found"
            ) from None

    def list_candidates(self) -> tuple[PracticeCandidate, ...]:
        return tuple(self._candidates[item] for item in self._order)

    def approved_practices(self) -> tuple[PracticeCandidate, ...]:
        """Only explicitly approved candidates enter the curated library."""
        return tuple(
            candidate for candidate in self.list_candidates() if candidate.is_approved
        )

    def review(
        self, candidate_id: UUID, *, reviewer: str | None = None
    ) -> PracticeCandidate:
        candidate = self.get(candidate_id)
        return self._save(
            replace(
                candidate,
                status=CandidateStatus.UNDER_REVIEW,
                reviewer=reviewer or candidate.reviewer,
            )
        )

    def approve(self, candidate_id: UUID, *, reviewer: str) -> PracticeCandidate:
        """Approve a candidate for the curated library (SPEC-032 §8).

        Approval is an explicit human action and is refused for any candidate
        that has not passed structural and feedback validation.
        """
        candidate = self.get(candidate_id)
        if candidate.status is CandidateStatus.APPROVED:
            raise CandidateNotApprovableError(
                f"candidate {candidate_id} is already approved"
            )
        if candidate.status is CandidateStatus.REJECTED:
            raise CandidateNotApprovableError(
                f"rejected candidate {candidate_id} cannot be approved"
            )
        if not candidate.validation.is_approvable:
            raise CandidateNotApprovableError(
                f"candidate {candidate_id} is not approvable: "
                + "; ".join(
                    candidate.validation.structural_errors
                    + candidate.validation.feedback_errors
                )
            )
        decided_at = datetime.now(UTC)
        return self._save(
            replace(
                candidate,
                status=CandidateStatus.APPROVED,
                reviewer=reviewer,
                decided_at=decided_at,
                provenance=replace(
                    candidate.provenance, reviewer=reviewer, decided_at=decided_at
                ),
            )
        )

    def reject(self, candidate_id: UUID, *, reviewer: str) -> PracticeCandidate:
        candidate = self.get(candidate_id)
        if candidate.status is CandidateStatus.APPROVED:
            raise CandidateNotApprovableError(
                f"approved candidate {candidate_id} cannot be rejected"
            )
        if candidate.status is CandidateStatus.REJECTED:
            raise CandidateNotApprovableError(
                f"candidate {candidate_id} is already rejected"
            )
        decided_at = datetime.now(UTC)
        return self._save(
            replace(
                candidate,
                status=CandidateStatus.REJECTED,
                reviewer=reviewer,
                decided_at=decided_at,
                provenance=replace(
                    candidate.provenance, reviewer=reviewer, decided_at=decided_at
                ),
            )
        )

    def edit(
        self,
        candidate_id: UUID,
        *,
        editor: str,
        title: str | None = None,
        description: str | None = None,
        contract: PracticeContentContract | None = None,
    ) -> PracticeCandidate:
        """Edit a candidate, keeping the superseded version for traceability.

        The approved practice is treated as authored Fablit content, not an
        immutable AI output (SPEC-032 §11).
        """
        candidate = self.get(candidate_id)
        history = candidate.history + (
            AuthoringRevision(
                version=candidate.revision,
                title=candidate.title,
                description=candidate.description,
                contract=candidate.contract,
                edited_at=datetime.now(UTC),
                editor=editor,
            ),
        )
        edited = replace(
            candidate,
            title=title.strip() if title is not None else candidate.title,
            description=(
                description.strip()
                if description is not None
                else candidate.description
            ),
            contract=contract if contract is not None else candidate.contract,
            status=CandidateStatus.UNDER_REVIEW,
            reviewer=editor,
            revision=candidate.revision + 1,
            history=history,
        )
        return self.add(edited)

    def _save(self, candidate: PracticeCandidate) -> PracticeCandidate:
        return self.add(candidate)
