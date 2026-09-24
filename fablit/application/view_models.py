"""Learner-facing view models for the practice flow (SPEC-012…022).

View models are the Application Layer's representations of domain state for
the Web/UI layer (SPEC-012 §26). They carry data only — no HTML, no
presentation formatting — so presentation concerns never leak into domain
objects. SPEC-015 adds the stimulus view model used to present the resolved
image to the learner (§24–26). SPEC-021 adds history and review views for
persistent practice completion records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PracticeActivitySummary:
    """A dashboard entry for one available practice activity."""

    id: UUID
    title: str
    description: str
    skills: tuple[str, ...]
    has_completed_practice: bool
    preview_image_url: str | None = None
    preview_alt_text: str | None = None


@dataclass(frozen=True)
class PracticeDashboardView:
    """The learner dashboard: the available practice activities (UC-001)."""

    activities: tuple[PracticeActivitySummary, ...]


@dataclass(frozen=True)
class StimulusView:
    """A resolved visual stimulus prepared for presentation (SPEC-015 §24–26)."""

    image_url: str
    alt_text: str
    attribution: str | None
    source_url: str


@dataclass(frozen=True)
class PracticeActivityView:
    """An activity prepared for learner practice (UC-002)."""

    id: UUID
    title: str
    description: str
    skills: tuple[str, ...]
    prompt: str
    stimulus: StimulusView | None = None


@dataclass(frozen=True)
class FeedbackView:
    """Learner-facing feedback derived from an Evaluation (UC-005)."""

    activity_title: str
    strengths: tuple[str, ...]
    improvements: tuple[str, ...]
    next_steps: tuple[str, ...]
    reflection_prompt: str


@dataclass(frozen=True)
class ReflectionView:
    """The purposeful reflection prompt with feedback context (UC-006)."""

    activity_title: str
    prompt: str
    context: str


@dataclass(frozen=True)
class CompletionView:
    """The completion confirmation shown after saving a Reflection (UC-007)."""

    message: str
    #: The authored next-practice continuation (SPEC-025 §3.1), when the
    #: completed activity has one. ``None`` keeps the completion page exactly
    #: as it was: the continuation is an invitation, never a forced step.
    continuation: ContinuationView | None = None


@dataclass(frozen=True)
class ContinuationView:
    """One authored next-practice continuation (SPEC-025 §3.1, §6).

    Presentation data for the quiet completion surface: the target practice
    and the authored copy that relates it to what the learner just did. It
    carries no recommendation, ranking, or learner-history signal.
    """

    target_activity_id: UUID
    target_title: str
    transition_copy: str


# SPEC-021: Practice History and Review Views


@dataclass(frozen=True)
class PracticeHistoryEntry:
    """A brief summary of one completed practice for history list (SPEC-021 §8).

    SPEC-021 §8: the history view should provide enough context to distinguish
    records: activity title, completion date/time, concise practice context,
    indication that the item can be reviewed.
    """

    completion_id: UUID
    activity_id: UUID
    activity_title: str
    completed_at: datetime
    submission_preview: str


@dataclass(frozen=True)
class PracticeHistoryView:
    """The learner's practice history list (SPEC-021 §8).

    SPEC-021 §8: history should make it easy to answer "What have I practised
    recently?" Recent completed practice appears first.

    Empty history is valid when the learner has no completed practice yet.
    """

    entries: tuple[PracticeHistoryEntry, ...]
    is_empty: bool


@dataclass(frozen=True)
class PracticeReviewView:
    """Review of a completed practice instance (SPEC-021 §9).

    SPEC-021 §9: selecting a completed practice allows the learner to review
    the meaningful parts of that specific practice instance. The review should
    expose:
    1. activity identity/title
    2. stimulus/context used for the practice
    3. original learner response
    4. evaluation result as currently defined by the application
    5. feedback
    6. learner reflection
    7. completion timestamp

    The review is a reflection and evidence surface, not a grading dashboard.
    """

    activity_title: str
    activity_id: UUID
    completed_at: datetime
    stimulus: StimulusView | None  # SPEC-021 §10: preserve original stimulus
    learner_response: str
    strengths: tuple[str, ...]
    improvements: tuple[str, ...]
    next_steps: tuple[str, ...]
    feedback: str
    reflection: str


# SPEC-022: Practice Mode Views


@dataclass(frozen=True)
class PracticeModeOption:
    """One selectable practice mode prepared for the learner (SPEC-022 §7)."""

    mode_id: str
    label: str
    description: str
    effort_guidance: str


@dataclass(frozen=True)
class PracticeModeChoiceView:
    """The calm, low-friction practice-mode choice (SPEC-022 §7).

    A small invitation, not a settings screen: the chooser never recommends,
    ranks, or pre-selects a mode (AC-022-10), and the existing Explore
    surface stays reachable (§9).
    """

    question: str
    modes: tuple[PracticeModeOption, ...]


@dataclass(frozen=True)
class PracticeModeActivitiesView:
    """The existing activities a chosen mode resolves to (SPEC-022 §3, §8).

    Reuse, not a parallel library: entries are the same dashboard summaries
    as the normal activity library, so choosing a mode always leads into the
    unchanged Assessment Activity and learner journey.
    """

    mode_id: str
    mode_label: str
    mode_description: str
    effort_guidance: str
    activities: tuple[PracticeActivitySummary, ...]
    is_empty: bool
