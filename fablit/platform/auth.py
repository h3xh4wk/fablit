from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AuthContext:
    principal: str | None = None
    scopes: list[str] | None = None
    active: bool = True


def parse_bearer_token(header_value: str | None) -> str | None:
    if not header_value:
        return None
    prefix = "Bearer "
    if header_value.startswith(prefix):
        return header_value[len(prefix) :].strip() or None
    return None


class IntrospectionClient:
    """A tiny client that can be mocked in tests by injecting a callable."""

    def __init__(
        self,
        introspect_fn: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        self._introspect_fn = introspect_fn or (
            lambda token: {"active": True, "sub": None}
        )

    def introspect(self, token: str | None) -> AuthContext:
        if not token:
            return AuthContext(active=False)
        payload = self._introspect_fn(token)
        scope = payload.get("scope")
        return AuthContext(
            principal=payload.get("sub"),
            scopes=list(scope.split()) if scope else [],
            active=bool(payload.get("active", False)),
        )
