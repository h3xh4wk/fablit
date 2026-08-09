"""Learning-domain models for Fablit (SPEC-005).

The domain layer is intentionally independent of platform infrastructure:
it can be imported and used in memory without persistence or framework
dependencies.
"""

from .activity import AssessmentActivity
from .assessment import Assessment
from .types import (
    ActivityStatus,
    ActivityType,
    AssessmentStatus,
    DomainError,
    DuplicateActivityPositionError,
    InvalidActivityError,
    InvalidAssessmentError,
)

__all__ = [
    "ActivityStatus",
    "ActivityType",
    "Assessment",
    "AssessmentActivity",
    "AssessmentStatus",
    "DomainError",
    "DuplicateActivityPositionError",
    "InvalidActivityError",
    "InvalidAssessmentError",
]
