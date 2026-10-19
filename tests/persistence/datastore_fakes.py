"""Shared fake Datastore entities that model Datastore's indexed-value limits.

The persistence tests use lightweight fake clients so they run without GCP
credentials. ``FakeEntity`` and the limit check are shared, because the adapter
behaviour they guard — an *indexed* string property longer than 1500 bytes
makes a write fail — applies to every Datastore-backed store, not just one.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Any

#: Datastore rejects an indexed string property longer than this many bytes.
INDEXED_STRING_LIMIT_BYTES = 1500


class InvalidArgumentError(Exception):
    """Mirrors google.api_core.exceptions.InvalidArgument for index limits."""


class FakeKey:
    """A stand-in for ``google.cloud.datastore.Key``."""

    def __init__(self, kind: str, name: str, namespace: str | None = None) -> None:
        self.kind = kind
        self.name = name
        self.namespace = namespace

    def _id(self) -> tuple[str, str, str | None]:
        return (self.kind, self.name, self.namespace)


class FakeEntity(dict[str, Any]):
    """A Datastore entity, optionally embedded, plus its non-indexed properties."""

    def __init__(
        self,
        key: FakeKey | None = None,
        exclude_from_indexes: Sequence[str] = (),
    ) -> None:
        super().__init__()
        self.key = key
        self.exclude_from_indexes = set(exclude_from_indexes)


def indexed_strings(
    value: Any, *, indexed: bool, name: str = ""
) -> Iterator[tuple[str, str]]:
    """Yield the ``(property, value)`` pairs Datastore would index.

    Mirrors the two rules the production error came from: an entity property is
    indexed unless that *same* entity excludes it, and properties nested in a
    bare ``dict`` are always indexed — an exclusion on the parent property does
    not propagate into it (googleapis/google-cloud-python#5111).
    """
    if isinstance(value, FakeEntity):
        for prop, item in value.items():
            yield from indexed_strings(
                item,
                indexed=prop not in value.exclude_from_indexes,
                name=prop,
            )
    elif isinstance(value, Mapping):
        for prop, item in value.items():
            yield from indexed_strings(item, indexed=True, name=prop)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from indexed_strings(item, indexed=indexed, name=name)
    elif isinstance(value, str) and indexed:
        yield name, value


def assert_within_index_limits(entity: FakeEntity) -> None:
    """Fail a write the way Datastore does when an indexed string is too long."""
    for name, text in indexed_strings(entity, indexed=True):
        if len(text.encode("utf-8")) > INDEXED_STRING_LIMIT_BYTES:
            raise InvalidArgumentError(
                f'The value of property "{name}" is longer than '
                f"{INDEXED_STRING_LIMIT_BYTES} bytes."
            )
