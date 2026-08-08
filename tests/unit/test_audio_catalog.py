from wispernext.audio.backend import FrameCallback
from wispernext.audio.catalog import MicrophoneCatalogService
from wispernext.audio.devices import ConnectionKind, InputDevice, ResolutionStatus
from wispernext.domain import MicrophoneSelectionMode
from wispernext.infrastructure.config import Settings


class MetadataOnlyBackend:
    def __init__(self, devices: tuple[InputDevice, ...], default_index: int | None) -> None:
        self.devices = devices
        self.default_index = default_index
        self.enumeration_count = 0
        self.default_read_count = 0
        self.stream_count = 0

    def enumerate_input_devices(self) -> tuple[InputDevice, ...]:
        self.enumeration_count += 1
        return self.devices

    def default_input_runtime_index(self) -> int | None:
        self.default_read_count += 1
        return self.default_index

    def create_input_stream(
        self, *, runtime_index: int, sample_rate: int, callback: FrameCallback
    ) -> object:
        self.stream_count += 1
        raise AssertionError("catalog must not open streams")


DEFAULT = InputDevice(
    5,
    "metadata:v1:default",
    "Default Mic",
    "Windows WASAPI",
    48_000,
    1,
    ConnectionKind.INTERNAL,
)
MANUAL = InputDevice(
    8,
    "metadata:v1:manual",
    "Manual Mic",
    "Windows WASAPI",
    48_000,
    1,
    ConnectionKind.USB,
)


def test_catalog_resolves_current_system_default_without_opening_stream() -> None:
    backend = MetadataOnlyBackend((DEFAULT, MANUAL), default_index=5)

    result = MicrophoneCatalogService(backend).resolve(Settings())

    assert result.status is ResolutionStatus.RESOLVED
    assert result.device == DEFAULT
    assert backend.default_read_count == 1
    assert backend.stream_count == 0


def test_catalog_resolves_manual_identity_without_reading_system_default() -> None:
    backend = MetadataOnlyBackend((DEFAULT, MANUAL), default_index=5)
    settings = Settings(
        microphone_selection_mode=MicrophoneSelectionMode.MANUAL,
        selected_microphone_id=MANUAL.stable_id,
    )

    result = MicrophoneCatalogService(backend).resolve(settings)

    assert result.status is ResolutionStatus.RESOLVED
    assert result.device == MANUAL
    assert backend.default_read_count == 0
    assert backend.stream_count == 0
