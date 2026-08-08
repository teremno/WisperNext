"""Side-effect-free composition root for implemented application services."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from wispernext.application import TranscriptionService
from wispernext.audio.backend import SoundDeviceBackend
from wispernext.audio.catalog import MicrophoneCatalogService
from wispernext.audio.session import AudioSessionService
from wispernext.domain import ApplicationStateMachine
from wispernext.groq import GroqTranscriptionTransportFactory
from wispernext.infrastructure.config import JsonSettingsStore
from wispernext.infrastructure.paths import UserPaths
from wispernext.infrastructure.secrets import (
    ChainedSecretProvider,
    CredentialManagerSecretProvider,
    EnvironmentSecretProvider,
    SecretProvider,
)
from wispernext.infrastructure.windows_credentials import WindowsCredentialStore


@dataclass(frozen=True, slots=True)
class ApplicationServices:
    """Constructed services; creating this object performs no external I/O."""

    state_machine: ApplicationStateMachine
    microphone_catalog: MicrophoneCatalogService
    audio_session: AudioSessionService
    settings_store: JsonSettingsStore
    secret_provider: SecretProvider
    transcription: TranscriptionService


def build_application_services(
    *,
    settings_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> ApplicationServices:
    """Create fresh service instances without loading files or opening resources."""
    resolved_path = settings_path or UserPaths.resolve(environ, home).settings_file
    audio_backend = SoundDeviceBackend()
    secret_provider: SecretProvider
    if environ is None:
        secret_provider = ChainedSecretProvider(
            CredentialManagerSecretProvider(WindowsCredentialStore()),
            EnvironmentSecretProvider(),
        )
    else:
        secret_provider = EnvironmentSecretProvider(environ)
    return ApplicationServices(
        state_machine=ApplicationStateMachine(),
        microphone_catalog=MicrophoneCatalogService(audio_backend),
        audio_session=AudioSessionService(audio_backend),
        settings_store=JsonSettingsStore(resolved_path),
        secret_provider=secret_provider,
        transcription=TranscriptionService(
            secret_provider,
            GroqTranscriptionTransportFactory(),
        ),
    )
