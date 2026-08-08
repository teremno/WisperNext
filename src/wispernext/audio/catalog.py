"""Read-only microphone catalog and explicit selection policy."""

from wispernext.audio.backend import AudioBackend
from wispernext.audio.devices import DeviceResolution, InputDevice, resolve_selection
from wispernext.domain import MicrophoneSelectionMode
from wispernext.infrastructure.config import Settings


class MicrophoneCatalogService:
    """Enumerate metadata and resolve the configured device without probing audio."""

    def __init__(self, backend: AudioBackend) -> None:
        self._backend = backend

    def list_devices(self) -> tuple[InputDevice, ...]:
        return self._backend.enumerate_input_devices()

    def resolve(self, settings: Settings) -> DeviceResolution:
        devices = self.list_devices()
        default_index = (
            self._backend.default_input_runtime_index()
            if settings.microphone_selection_mode is MicrophoneSelectionMode.SYSTEM_DEFAULT
            else None
        )
        return resolve_selection(
            settings.microphone_selection_mode,
            settings.selected_microphone_id,
            devices,
            default_index,
        )
