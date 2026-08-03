from wispernext.audio.devices import (
    ConnectionKind,
    DevicePreference,
    InputDevice,
    ResolutionStatus,
    build_stable_id,
    infer_connection_kind,
    resolve_device,
)


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
