"""Metadata-only microphone catalog and stable preference resolution."""

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum


class ConnectionKind(StrEnum):
    INTERNAL = "internal"
    USB = "usb"
    BLUETOOTH = "bluetooth"
    WEBCAM = "webcam"
    VIRTUAL = "virtual"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class InputDevice:
    runtime_index: int
    stable_id: str
    name: str
    host_api: str
    default_sample_rate: int
    max_input_channels: int
    connection_kind: ConnectionKind


@dataclass(frozen=True, slots=True)
class DevicePreference:
    stable_id: str
    last_seen_name: str
    last_seen_host_api: str
    last_seen_sample_rate: int
    last_seen_channels: int

    @classmethod
    def from_device(cls, device: InputDevice) -> "DevicePreference":
        return cls(
            device.stable_id,
            device.name,
            device.host_api,
            device.default_sample_rate,
            device.max_input_channels,
        )


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class DeviceResolution:
    status: ResolutionStatus
    device: InputDevice | None = None


def build_stable_id(
    name: str, host_api: str, default_sample_rate: int, max_input_channels: int
) -> str:
    """Build a non-index preference key from stable metadata exposed by PortAudio."""
    normalized = "|".join(
        (
            _normalize(name),
            _normalize(host_api),
            str(default_sample_rate),
            str(max_input_channels),
        )
    )
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
    return f"metadata:v1:{digest}"


def infer_connection_kind(name: str) -> ConnectionKind:
    normalized = _normalize(name)
    keywords = (
        (ConnectionKind.BLUETOOTH, ("bluetooth", "hands-free", "airpods", "buds")),
        (ConnectionKind.USB, ("usb",)),
        (ConnectionKind.WEBCAM, ("webcam", "camera")),
        (ConnectionKind.VIRTUAL, ("virtual", "cable", "voicemeeter")),
        (ConnectionKind.INTERNAL, ("array", "internal", "realtek")),
    )
    for kind, candidates in keywords:
        if any(candidate in normalized for candidate in candidates):
            return kind
    return ConnectionKind.UNKNOWN


def resolve_device(
    preference: DevicePreference, devices: tuple[InputDevice, ...]
) -> DeviceResolution:
    """Resolve one explicit preference without guessing or physical fallback."""
    matches = tuple(device for device in devices if device.stable_id == preference.stable_id)
    if len(matches) == 1:
        return DeviceResolution(ResolutionStatus.RESOLVED, matches[0])
    if len(matches) > 1:
        return DeviceResolution(ResolutionStatus.AMBIGUOUS)
    return DeviceResolution(ResolutionStatus.NOT_FOUND)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())
