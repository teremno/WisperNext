"""Windows-appropriate per-user data paths."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class UserPaths:
    """Application-owned locations outside the source and install trees."""

    data_dir: Path
    settings_file: Path
    logs_dir: Path

    @classmethod
    def resolve(
        cls,
        environ: Mapping[str, str] | None = None,
        home: Path | None = None,
    ) -> "UserPaths":
        """Resolve `%LOCALAPPDATA%`, with a deterministic Windows-style fallback."""
        environment = os.environ if environ is None else environ
        local_app_data = environment.get("LOCALAPPDATA", "").strip()
        base = (
            Path(local_app_data) if local_app_data else (home or Path.home()) / "AppData" / "Local"
        )
        data_dir = base / "WisperNext"
        return cls(data_dir, data_dir / "settings.json", data_dir / "logs")
