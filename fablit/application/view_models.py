"""Learner-facing view models for the practice flow (SPEC-012).

View models are the Application Layer's representations of domain state for
the Web/UI layer (SPEC-012 §26). They carry data only — no HTML, no
presentation formatting — so presentation concerns never leak into domain
objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PracticeActivitySummary:
    """A dashboard entry for one available practice activity."""

    id: UUID
    title: str
    description: str
    skills: tuple[str, ...]


@dataclass(frozen=True)
class PracticeDashboardView:
    """The learner dashboard: the available practice activities (UC-001)."""

    activities: tuple[PracticeActivitySummary, ...]


@dataclass(frozen=True)
class PracticeActivityView:
    """An activity prepared for learner practice (UC-002)."""

    id: UUID
    title: str
    description: str
    skills: tuple[str, ...]
    prompt: str


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
