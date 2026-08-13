"""Learning-domain models for Fablit (SPEC-005 through SPEC-009).

The domain layer is intentionally independent of platform infrastructure:
it can be imported and used in memory without persistence or framework
dependencies.
"""

from .activity import AssessmentActivity
from .assessment import Assessment
from .evaluation import Evaluation, EvaluationFinding
from .feedback import Feedback
from .reflection import Reflection
from .submission import Submission
from .types import (
    ActivityStatus,
    ActivityType,
    AssessmentStatus,
    DomainError,
    DuplicateActivityPositionError,
    InvalidActivityError,
    InvalidAssessmentError,
    InvalidEvaluationError,
    InvalidEvaluationFindingError,
    InvalidFeedbackError,
    InvalidReflectionError,
    InvalidSubmissionError,
    InvalidSubmissionTransitionError,
    SubmissionStatus,
)

__all__ = [
    "ActivityStatus",
    "ActivityType",
    "Assessment",
    "AssessmentActivity",
    "AssessmentStatus",
    "DomainError",
    "DuplicateActivityPositionError",
    "Evaluation",
    "EvaluationFinding",
    "Feedback",
    "InvalidActivityError",
    "InvalidAssessmentError",
    "InvalidEvaluationError",
    "InvalidEvaluationFindingError",
    "InvalidFeedbackError",
    "InvalidReflectionError",
    "InvalidSubmissionError",
    "InvalidSubmissionTransitionError",
    "Reflection",
    "Submission",
    "SubmissionStatus",
]
