"""Application layer for the learner practice flow (SPEC-012).

The application layer orchestrates the existing learning-domain models into
the first learner-facing vertical slice. It contains no HTML and no
presentation logic: it prepares learner-facing view models for the Web/UI
layer and preserves the domain boundaries established by SPEC-005–011.
"""

from .demo_data import (
    DEMO_LEARNER_ID,
    REFLECTION_PROMPT,
    build_demo_activities,
    build_demo_findings,
    build_demo_skills,
)
from .demo_evaluator import DemoEvaluator
from .errors import (
    ActivityNotFoundError,
    ApplicationError,
    CompletionNotFoundError,
    FeedbackNotFoundError,
    InvalidPracticeResponseError,
    InvalidReflectionResponseError,
    JourneyStateError,
)
from .store import DemoActivity, LearnerJourneyStore
from .use_cases import PracticeApplication
from .view_models import (
    CompletionView,
    FeedbackView,
    PracticeActivitySummary,
    PracticeActivityView,
    PracticeDashboardView,
    ReflectionView,
)

__all__ = [
    "ActivityNotFoundError",
    "ApplicationError",
    "CompletionNotFoundError",
    "CompletionView",
    "DEMO_LEARNER_ID",
    "DemoActivity",
    "DemoEvaluator",
    "FeedbackNotFoundError",
    "FeedbackView",
    "InvalidPracticeResponseError",
    "InvalidReflectionResponseError",
    "JourneyStateError",
    "LearnerJourneyStore",
    "PracticeActivitySummary",
    "PracticeActivityView",
    "PracticeApplication",
    "PracticeDashboardView",
    "REFLECTION_PROMPT",
    "ReflectionView",
    "build_demo_activities",
    "build_demo_findings",
    "build_demo_skills",
]
