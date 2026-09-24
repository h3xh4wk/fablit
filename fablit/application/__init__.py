"""Application layer for the learner practice flow (SPEC-012, SPEC-015, SPEC-022).

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
    PRACTICE_CAPABILITIES,
    PRACTICE_CAPABILITY_ARTICULATE,
    PRACTICE_CAPABILITY_IDEATE,
    PRACTICE_CAPABILITY_INTERPRET,
    PRACTICE_CAPABILITY_OBSERVE,
    PRACTICE_CAPABILITY_REFLECT,
    PRACTICE_MODE_CHOICE_QUESTION,
    REFLECTION_PROMPT,
    SHORT_DRILL_ACTIVITY_TITLES,
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
    SubmissionInProgressError,
    UnknownPracticeModeError,
)
from .practice_continuity import (
    CONTINUATION_ACTION_LABEL,
    CONTINUATION_HEADING,
    PracticeTransition,
    build_practice_transition_map,
    build_practice_transitions,
)
from .practice_modes import (
    PracticeMode,
    PracticeModeDefinition,
    build_practice_mode_definitions,
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
from .store import Concept, DemoActivity, LearnerJourneyStore, PracticeCompletion
from .use_cases import PracticeApplication
from .view_models import (
    CompletionView,
    ContinuationView,
    FeedbackView,
    PracticeActivitySummary,
    PracticeActivityView,
    PracticeDashboardView,
    PracticeModeActivitiesView,
    PracticeModeChoiceView,
    PracticeModeOption,
    ReflectionView,
    StimulusView,
)

__all__ = [
    "ActivityNotFoundError",
    "ApplicationError",
    "CompletionNotFoundError",
    "CompletionView",
    "Concept",
    "CONTINUATION_ACTION_LABEL",
    "CONTINUATION_HEADING",
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
    "PRACTICE_CAPABILITIES",
    "PRACTICE_CAPABILITY_ARTICULATE",
    "PRACTICE_CAPABILITY_IDEATE",
    "PRACTICE_CAPABILITY_INTERPRET",
    "PRACTICE_CAPABILITY_OBSERVE",
    "PRACTICE_CAPABILITY_REFLECT",
    "PRACTICE_MODE_CHOICE_QUESTION",
    "PracticeActivitySummary",
    "PracticeActivityView",
    "PracticeApplication",
    "PracticeDashboardView",
    "PracticeCompletion",
    "PracticeMode",
    "PracticeModeActivitiesView",
    "PracticeModeChoiceView",
    "PracticeModeDefinition",
    "PracticeModeOption",
    "PracticeTransition",
    "REFLECTION_PROMPT",
    "ReflectionView",
    "ResilientStimulusProvider",
    "SHORT_DRILL_ACTIVITY_TITLES",
    "StimulusProvider",
    "StimulusRetrievalError",
    "StimulusView",
    "SubmissionInProgressError",
    "SUPPORTED_PROVIDERS",
    "UnknownPracticeModeError",
    "WikimediaCommonsProvider",
    "ContinuationView",
    "build_demo_activities",
    "build_demo_activity_map",
    "build_demo_skills",
    "build_fallback_stimuli",
    "build_practice_mode_definitions",
    "build_practice_transition_map",
    "build_practice_transitions",
    "build_stimulus_provider",
]
