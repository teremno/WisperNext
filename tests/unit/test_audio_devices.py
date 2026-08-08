from wispernext.audio.devices import (
    ConnectionKind,
    DevicePreference,
    InputDevice,
    ResolutionStatus,
    build_stable_id,
    infer_connection_kind,
    resolve_device,
    resolve_selection,
)
from wispernext.domain import MicrophoneSelectionMode


def device(index: int, *, name: str = "USB Mic") -> InputDevice:
    stable_id = build_stable_id(name, "Windows WASAPI", 48_000, 1)
    return InputDevice(index, stable_id, name, "Windows WASAPI", 48_000, 1, ConnectionKind.USB)


def test_identity_survives_runtime_index_changes() -> None:
    original = device(2)
    moved = device(19)

    result = resolve_device(DevicePreference.from_device(original), (moved,))

    assert result.status is ResolutionStatus.RESOLVED
    assert result.device == moved


def test_resolution_never_guesses_missing_or_ambiguous_device() -> None:
    preference = DevicePreference.from_device(device(1))

    missing = resolve_device(preference, (device(2, name="Other Mic"),))
    ambiguous = resolve_device(preference, (device(3), device(4)))

    assert missing.status is ResolutionStatus.NOT_FOUND
    assert missing.device is None
    assert ambiguous.status is ResolutionStatus.AMBIGUOUS
    assert ambiguous.device is None


def test_connection_kind_is_metadata_only() -> None:
    assert infer_connection_kind("Bluetooth Headset Hands-Free") is ConnectionKind.BLUETOOTH
    assert infer_connection_kind("HD USB Camera") is ConnectionKind.USB
    assert infer_connection_kind("VB-Audio Virtual Cable") is ConnectionKind.VIRTUAL


def test_system_default_resolves_only_the_current_runtime_default() -> None:
    devices = (device(2), device(7, name="Other Mic"))

    result = resolve_selection(MicrophoneSelectionMode.SYSTEM_DEFAULT, None, devices, 7)

    assert result.status is ResolutionStatus.RESOLVED
    assert result.device == devices[1]


def test_manual_selection_resolves_stable_id_after_runtime_index_change() -> None:
    selected = device(3)
    moved = device(21)

    result = resolve_selection(
        MicrophoneSelectionMode.MANUAL,
        selected.stable_id,
        (moved,),
        default_runtime_index=3,
    )

    assert result.status is ResolutionStatus.RESOLVED
    assert result.device == moved


def test_selection_never_falls_back_when_default_or_manual_device_is_missing() -> None:
    available = (device(4, name="Available Mic"),)

    missing_default = resolve_selection(MicrophoneSelectionMode.SYSTEM_DEFAULT, None, available, 99)
    missing_manual = resolve_selection(
        MicrophoneSelectionMode.MANUAL, "metadata:v1:missing", available, 4
    )

    assert missing_default.status is ResolutionStatus.NOT_FOUND
    assert missing_manual.status is ResolutionStatus.NOT_FOUND
