"""Shared construction helpers for learning-domain tests."""

from __future__ import annotations

from typing import Any

from fablit.domain import (
    ActivityStatus,
    ActivityType,
    Assessment,
    AssessmentActivity,
    AssessmentStatus,
)


def make_activity(**overrides: Any) -> AssessmentActivity:
    """Build a valid AssessmentActivity, overriding any field via kwargs."""
    values: dict[str, Any] = {
        "activity_type": ActivityType.WRITTEN_RESPONSE,
        "instructions": "Write a short response to the prompt.",
        "position": 0,
        "status": ActivityStatus.ACTIVE,
    }
    values.update(overrides)
    return AssessmentActivity(**values)


def make_assessment(**overrides: Any) -> Assessment:
    """Build a valid Assessment, overriding any field via kwargs."""
    values: dict[str, Any] = {
        "title": "Daily Practice",
        "description": "A short daily practice session.",
        "status": AssessmentStatus.DRAFT,
        "activities": (make_activity(position=0), make_activity(position=1)),
    }
    values.update(overrides)
    return Assessment(**values)
