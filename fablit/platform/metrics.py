from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Counter:
    name: str
    value: float = 0.0

    def inc(self, amount: float = 1.0) -> None:
        self.value += amount


class MetricsRegistry:
    """A tiny in-memory metrics registry used by examples and tests."""

    def __init__(self) -> None:
        self._counters: dict[str, Counter] = {}

    def counter(self, name: str) -> Counter:
        if name not in self._counters:
            self._counters[name] = Counter(name=name)
        return self._counters[name]

    def render(self) -> str:
        lines = [
            f"{name} {counter.value}"
            for name, counter in sorted(self._counters.items())
        ]
        return "\n".join(lines)
