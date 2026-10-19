"""Shared Google Cloud Datastore entity helpers (SPEC-021 / SPEC-032 / SPEC-035).

Each Datastore-backed store in :mod:`fablit.platform` keeps a small set of
queried properties next to large free-text payloads (practice completions,
authoring candidates, published practices). Datastore rejects an *indexed*
string property longer than :data:`INDEXED_STRING_LIMIT_BYTES`, which fails
the entire write, so payload values must be stored unindexed.

An ``exclude_from_indexes`` entry on the parent property does not propagate
into a value stored as a bare ``dict``: the exclusion has to live on the
nested value itself, so nested payloads must be real ``Entity`` instances
(googleapis/google-cloud-python#5111). :func:`embedded_entity` and
:func:`unindexed_value` build exactly that, recursively, so a payload can be
handed over as an ordinary mapping or sequence.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

#: Datastore rejects an *indexed* string property longer than this many bytes.
INDEXED_STRING_LIMIT_BYTES = 1500


def embedded_entity(client: Any, properties: Mapping[str, Any]) -> dict[str, Any]:
    """Build a Datastore embedded entity whose properties are not indexed.

    Use this for a payload that is only ever read back by key and never
    queried, so that long generated or learner-written text cannot fail the
    write on Datastore's indexed-value limit.

    Args:
        client: A ``google.cloud.datastore.Client`` (or a test double).
        properties: The payload to store unindexed.

    Returns:
        An entity Datastore stores without indexing any of its values.
    """
    converted = {
        name: unindexed_value(client, value) for name, value in properties.items()
    }
    entity: dict[str, Any] = client.entity(exclude_from_indexes=tuple(converted))
    entity.update(converted)
    return entity


def unindexed_value(client: Any, value: Any) -> Any:
    """Convert one property value so Datastore stores it without indexes.

    Nested mappings become embedded entities and sequences have their items
    converted in place, so the value still reads back as an ordinary mapping
    or sequence after a round trip.

    Args:
        client: A ``google.cloud.datastore.Client`` (or a test double).
        value: The property value to store unindexed.

    Returns:
        The value, with every nested mapping replaced by an embedded entity.
    """
    if isinstance(value, Mapping):
        return embedded_entity(client, value)
    if isinstance(value, list | tuple):
        return [unindexed_value(client, item) for item in value]
    return value
