"""Side-effect-free composition root for implemented application services."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from wispernext.audio.backend import SoundDeviceBackend
from wispernext.audio.session import AudioSessionService
from wispernext.domain import ApplicationStateMachine
from wispernext.infrastructure.config import JsonSettingsStore
from wispernext.infrastructure.paths import UserPaths
from wispernext.infrastructure.secrets import EnvironmentSecretProvider, SecretProvider


@dataclass(frozen=True, slots=True)
class ApplicationServices:
    """Constructed services; creating this object performs no external I/O."""

    state_machine: ApplicationStateMachine
    audio_session: AudioSessionService
    settings_store: JsonSettingsStore
    secret_provider: SecretProvider


def build_application_services(
    *,
    settings_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> ApplicationServices:
    """Create fresh service instances without loading files or opening resources."""
    resolved_path = settings_path or UserPaths.resolve(environ, home).settings_file
    audio_backend = SoundDeviceBackend()
    return ApplicationServices(
        state_machine=ApplicationStateMachine(),
        audio_session=AudioSessionService(audio_backend),
        settings_store=JsonSettingsStore(resolved_path),
        secret_provider=EnvironmentSecretProvider(environ),
    )
