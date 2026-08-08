from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_snake_case(value: str) -> str:
    return "".join(
        f"_{char.lower()}" if char.isupper() else char for char in value
    ).strip("_")
