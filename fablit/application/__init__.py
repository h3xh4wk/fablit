"""Application layer for the learner practice flow (SPEC-012, SPEC-015).

The application layer orchestrates the existing learning-domain models into
the first learner-facing vertical slice. It contains no HTML and no
presentation logic: it prepares learner-facing view models for the Web/UI
layer and preserves the domain boundaries established by SPEC-005–011.
SPEC-015 adds the stimulus provider abstraction (external image retrieval
isolated behind an application-level boundary) and the response-aware
evaluator contract.
"""

from .demo_data import (
    DEMO_LEARNER_ID,
    REFLECTION_PROMPT,
    build_demo_activities,
    build_demo_activity_map,
    build_demo_skills,
)
from .demo_evaluator import DemoEvaluator, Evaluator
from .errors import (
    ActivityNotFoundError,
    ApplicationError,
    CompletionNotFoundError,
    EvaluationFailedError,
    FeedbackNotFoundError,
    InvalidPracticeResponseError,
    InvalidReflectionResponseError,
    JourneyStateError,
    StimulusRetrievalError,
)
from .stimulus import (
    SUPPORTED_PROVIDERS,
    FallbackDefinition,
    FallbackStimulusProvider,
    ResilientStimulusProvider,
    StimulusProvider,
    WikimediaCommonsProvider,
    build_fallback_stimuli,
    build_stimulus_provider,
)
from .store import Concept, DemoActivity, LearnerJourneyStore
from .use_cases import PracticeApplication
from .view_models import (
    CompletionView,
    FeedbackView,
    PracticeActivitySummary,
    PracticeActivityView,
    PracticeDashboardView,
    ReflectionView,
    StimulusView,
)

__all__ = [
    "ActivityNotFoundError",
    "ApplicationError",
    "CompletionNotFoundError",
    "CompletionView",
    "Concept",
    "DEMO_LEARNER_ID",
    "DemoActivity",
    "DemoEvaluator",
    "EvaluationFailedError",
    "Evaluator",
    "FallbackDefinition",
    "FallbackStimulusProvider",
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
    "ResilientStimulusProvider",
    "StimulusProvider",
    "StimulusRetrievalError",
    "StimulusView",
    "SUPPORTED_PROVIDERS",
    "WikimediaCommonsProvider",
    "build_demo_activities",
    "build_demo_activity_map",
    "build_demo_skills",
    "build_fallback_stimuli",
    "build_stimulus_provider",
]
