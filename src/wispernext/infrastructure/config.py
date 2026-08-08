"""Versioned application settings and atomic JSON persistence."""

import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Final, cast
from uuid import uuid4

from wispernext.domain import MicrophoneSelectionMode

CURRENT_SCHEMA_VERSION: Final = 2
MIN_RECORDING_SECONDS: Final = 5
MAX_RECORDING_SECONDS: Final = 1_800


class LanguageCode(StrEnum):
    """Language choices required by the first stable product specification."""

    ENGLISH = "en"
    UKRAINIAN = "uk"
    GERMAN = "de"
    FRENCH = "fr"
    SPANISH = "es"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    POLISH = "pl"
    DUTCH = "nl"
    TURKISH = "tr"
    ARABIC = "ar"
    HINDI = "hi"
    CHINESE_SIMPLIFIED = "zh-CN"
    JAPANESE = "ja"
    KOREAN = "ko"


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated non-secret application settings."""

    schema_version: int = CURRENT_SCHEMA_VERSION
    microphone_selection_mode: MicrophoneSelectionMode = MicrophoneSelectionMode.SYSTEM_DEFAULT
    selected_microphone_id: str | None = None
    hotkey: str = "F8"
    auto_paste: bool = False
    autostart: bool = False
    max_recording_seconds: int = 300
    launch_floating_button: bool = True
    input_language: LanguageCode | None = None
    output_language: LanguageCode | None = None
    safe_formatting: bool = True
    transcription_model: str = "whisper-large-v3-turbo"
    text_model: str = "llama-3.3-70b-versatile"


@dataclass(frozen=True, slots=True)
class SettingsLoadResult:
    """Settings plus recovery evidence for diagnostics."""

    settings: Settings
    recovered_from_invalid: bool = False
    preserved_invalid_path: Path | None = None


class SettingsValidationError(ValueError):
    """Raised when settings content violates the supported schema."""


class SettingsStorageError(RuntimeError):
    """Raised when settings cannot be safely preserved or persisted."""


_FIELDS: Final = frozenset(Settings.__dataclass_fields__)
_VERSION_ZERO_FIELDS: Final = _FIELDS - {"schema_version", "microphone_selection_mode"}
_VERSION_ONE_FIELDS: Final = _FIELDS - {"microphone_selection_mode"}


def decode_settings(payload: object) -> Settings:
    """Migrate and validate untrusted JSON-compatible settings content."""
    if not isinstance(payload, dict):
        raise SettingsValidationError("Settings root must be an object.")

    raw = cast(dict[object, object], payload)
    if any(not isinstance(key, str) for key in raw):
        raise SettingsValidationError("Settings field names must be strings.")
    values = cast(dict[str, object], raw)
    version = values.get("schema_version", 0)
    if type(version) is not int:
        raise SettingsValidationError("schema_version must be an integer.")
    is_version_zero = version == 0
    if is_version_zero:
        unknown = set(values) - _VERSION_ZERO_FIELDS
        if unknown:
            raise SettingsValidationError(f"Unknown settings fields: {sorted(unknown)!r}.")
        selection_mode = (
            MicrophoneSelectionMode.MANUAL.value
            if values.get("selected_microphone_id") is not None
            else MicrophoneSelectionMode.SYSTEM_DEFAULT.value
        )
        values = {
            **values,
            "schema_version": CURRENT_SCHEMA_VERSION,
            "microphone_selection_mode": selection_mode,
        }
    elif version == 1:
        unknown = set(values) - _VERSION_ONE_FIELDS
        missing = _VERSION_ONE_FIELDS - set(values)
        if unknown:
            raise SettingsValidationError(f"Unknown settings fields: {sorted(unknown)!r}.")
        if missing:
            raise SettingsValidationError(f"Missing settings fields: {sorted(missing)!r}.")
        selection_mode = (
            MicrophoneSelectionMode.MANUAL.value
            if values.get("selected_microphone_id") is not None
            else MicrophoneSelectionMode.SYSTEM_DEFAULT.value
        )
        values = {
            **values,
            "schema_version": CURRENT_SCHEMA_VERSION,
            "microphone_selection_mode": selection_mode,
        }
    elif version != CURRENT_SCHEMA_VERSION:
        raise SettingsValidationError(f"Unsupported settings schema version: {version}.")

    unknown = set(values) - _FIELDS
    missing = _FIELDS - set(values)
    if unknown:
        raise SettingsValidationError(f"Unknown settings fields: {sorted(unknown)!r}.")
    if missing and not is_version_zero:
        raise SettingsValidationError(f"Missing settings fields: {sorted(missing)!r}.")
    defaults = asdict(Settings())
    merged = {**defaults, **values}

    _require_exact_int(merged, "schema_version", CURRENT_SCHEMA_VERSION, CURRENT_SCHEMA_VERSION)
    selection_mode = _microphone_selection_mode(merged)
    selected_id = _optional_string(merged, "selected_microphone_id", max_length=512)
    if selection_mode is MicrophoneSelectionMode.MANUAL and selected_id is None:
        raise SettingsValidationError("Manual microphone selection requires a stable device ID.")
    if selection_mode is MicrophoneSelectionMode.SYSTEM_DEFAULT and selected_id is not None:
        raise SettingsValidationError(
            "System-default selection must not retain a manual device ID."
        )
    hotkey = _required_string(merged, "hotkey", max_length=64)
    auto_paste = _required_bool(merged, "auto_paste")
    autostart = _required_bool(merged, "autostart")
    max_seconds = _require_exact_int(
        merged,
        "max_recording_seconds",
        MIN_RECORDING_SECONDS,
        MAX_RECORDING_SECONDS,
    )
    launch_button = _required_bool(merged, "launch_floating_button")
    input_language = _optional_language(merged, "input_language")
    output_language = _optional_language(merged, "output_language")
    safe_formatting = _required_bool(merged, "safe_formatting")
    transcription_model = _required_string(merged, "transcription_model", max_length=128)
    text_model = _required_string(merged, "text_model", max_length=128)

    return Settings(
        microphone_selection_mode=selection_mode,
        selected_microphone_id=selected_id,
        hotkey=hotkey,
        auto_paste=auto_paste,
        autostart=autostart,
        max_recording_seconds=max_seconds,
        launch_floating_button=launch_button,
        input_language=input_language,
        output_language=output_language,
        safe_formatting=safe_formatting,
        transcription_model=transcription_model,
        text_model=text_model,
    )


def encode_settings(settings: Settings) -> dict[str, object]:
    """Return a JSON-compatible settings object containing no secrets."""
    return {
        "schema_version": settings.schema_version,
        "microphone_selection_mode": settings.microphone_selection_mode.value,
        "selected_microphone_id": settings.selected_microphone_id,
        "hotkey": settings.hotkey,
        "auto_paste": settings.auto_paste,
        "autostart": settings.autostart,
        "max_recording_seconds": settings.max_recording_seconds,
        "launch_floating_button": settings.launch_floating_button,
        "input_language": settings.input_language.value if settings.input_language else None,
        "output_language": settings.output_language.value if settings.output_language else None,
        "safe_formatting": settings.safe_formatting,
        "transcription_model": settings.transcription_model,
        "text_model": settings.text_model,
    }


class JsonSettingsStore:
    """Load and atomically save settings at an injected per-user path."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> SettingsLoadResult:
        """Load settings, preserving invalid content before using safe defaults."""
        if not self._path.exists():
            return SettingsLoadResult(Settings())
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            return SettingsLoadResult(decode_settings(payload))
        except (OSError, UnicodeError, json.JSONDecodeError, SettingsValidationError) as exc:
            preserved = self._preserve_invalid_file(exc)
            return SettingsLoadResult(Settings(), True, preserved)

    def save(self, settings: Settings) -> None:
        """Persist validated settings using flush, fsync, and atomic replace."""
        validated = decode_settings(encode_settings(settings))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=f".{self._path.name}.",
                suffix=".tmp",
                dir=self._path.parent,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(encode_settings(validated), temporary, ensure_ascii=False, indent=2)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self._path)
        except OSError as exc:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise SettingsStorageError("Could not atomically save settings.") from exc

    def _preserve_invalid_file(self, cause: Exception) -> Path:
        preserved = self._path.with_name(
            f"{self._path.stem}.corrupt-{uuid4().hex}{self._path.suffix}"
        )
        try:
            os.replace(self._path, preserved)
        except OSError as exc:
            raise SettingsStorageError("Could not preserve invalid settings.") from exc
        if not preserved.exists():
            raise SettingsStorageError(
                "Invalid settings preservation was not confirmed."
            ) from cause
        return preserved


def _required_bool(values: Mapping[str, object], field: str) -> bool:
    value = values[field]
    if type(value) is not bool:
        raise SettingsValidationError(f"{field} must be a boolean.")
    return value


def _require_exact_int(values: Mapping[str, object], field: str, minimum: int, maximum: int) -> int:
    value = values[field]
    if type(value) is not int or not minimum <= value <= maximum:
        raise SettingsValidationError(f"{field} must be an integer from {minimum} to {maximum}.")
    return value


def _required_string(values: Mapping[str, object], field: str, max_length: int) -> str:
    value = values[field]
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise SettingsValidationError(f"{field} must be a non-empty string.")
    return value


def _optional_string(values: Mapping[str, object], field: str, max_length: int) -> str | None:
    value = values[field]
    if value is None:
        return None
    return _required_string(values, field, max_length)


def _optional_language(values: Mapping[str, object], field: str) -> LanguageCode | None:
    value = values[field]
    if value is None:
        return None
    if not isinstance(value, str):
        raise SettingsValidationError(f"{field} must be a supported language code or null.")
    try:
        return LanguageCode(value)
    except ValueError as exc:
        raise SettingsValidationError(
            f"{field} must be a supported language code or null."
        ) from exc


def _microphone_selection_mode(values: Mapping[str, object]) -> MicrophoneSelectionMode:
    value = values["microphone_selection_mode"]
    if not isinstance(value, str):
        raise SettingsValidationError("microphone_selection_mode must be a supported value.")
    try:
        return MicrophoneSelectionMode(value)
    except ValueError as exc:
        raise SettingsValidationError(
            "microphone_selection_mode must be a supported value."
        ) from exc
