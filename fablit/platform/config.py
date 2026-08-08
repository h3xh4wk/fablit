from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fablit.config import AppConfig, _resolve_environment_overrides


@dataclass(slots=True)
class RemoteOverride:
    path: str | None = None
    values: dict[str, Any] | None = None


class ConfigLoader:
    """Load configuration from env vars, files, and remote overrides."""

    def __init__(
        self,
        remote_overrides: list[RemoteOverride] | None = None,
    ) -> None:
        self.remote_overrides = remote_overrides or []

    def load(self, *, config_path: str | None = None) -> AppConfig:
        config_data: dict[str, Any] = {}
        config_file_path: Path | None = None

        if config_path is None:
            config_path = os.getenv("FABLIT_CONFIG")

        if config_path:
            config_file_path = Path(config_path)
            if config_file_path.exists():
                config_data.update(
                    json.loads(config_file_path.read_text(encoding="utf-8"))
                )
            else:
                raise FileNotFoundError(config_file_path)

        for override in self.remote_overrides:
            if override.values:
                config_data.update(override.values)
            if override.path:
                override_path = Path(override.path)
                if override_path.exists():
                    config_file_path = override_path
                    config_data.update(
                        json.loads(override_path.read_text(encoding="utf-8"))
                    )

        config_data.update(_resolve_environment_overrides())

        if config_file_path is not None:
            config_data["config_file"] = config_file_path

        return AppConfig(**config_data)
