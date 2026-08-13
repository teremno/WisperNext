"""Side-effect-free composition root for implemented application services."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from wispernext.application import (
    AutoPasteService,
    ClipboardDeliveryService,
    DiagnosticJournal,
    PastePort,
    TextProcessingService,
    TranscriptionService,
)
from wispernext.audio.backend import SoundDeviceBackend
from wispernext.audio.catalog import MicrophoneCatalogService
from wispernext.audio.session import AudioSessionService
from wispernext.domain import ApplicationStateMachine
from wispernext.groq import GroqTextProcessingTransportFactory, GroqTranscriptionTransportFactory
from wispernext.infrastructure.config import JsonSettingsStore
from wispernext.infrastructure.diagnostics import RotatingDiagnosticJournal
from wispernext.infrastructure.paths import UserPaths
from wispernext.infrastructure.secrets import (
    ChainedSecretProvider,
    CredentialManagerSecretProvider,
    EnvironmentSecretProvider,
    SecretProvider,
)
from wispernext.infrastructure.windows_credentials import WindowsCredentialStore
from wispernext.platform.windows.clipboard import WindowsClipboard, WindowsPasteAdapter


@dataclass(frozen=True, slots=True)
class ApplicationServices:
    """Constructed services; creating this object performs no external I/O."""

    state_machine: ApplicationStateMachine
    microphone_catalog: MicrophoneCatalogService
    audio_session: AudioSessionService
    settings_store: JsonSettingsStore
    secret_provider: SecretProvider
    transcription: TranscriptionService
    text_processing: TextProcessingService
    clipboard_delivery: ClipboardDeliveryService
    auto_paste: AutoPasteService
    focus_port: PastePort
    diagnostic_journal: DiagnosticJournal


def build_application_services(
    *,
    settings_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> ApplicationServices:
    """Create fresh service instances without loading files or opening resources."""
    user_paths = UserPaths.resolve(environ, home)
    resolved_path = settings_path or user_paths.settings_file
    logs_dir = resolved_path.parent / "logs" if settings_path is not None else user_paths.logs_dir
    audio_backend = SoundDeviceBackend()
    secret_provider: SecretProvider
    if environ is None:
        secret_provider = ChainedSecretProvider(
            CredentialManagerSecretProvider(WindowsCredentialStore()),
            EnvironmentSecretProvider(),
        )
    else:
        secret_provider = EnvironmentSecretProvider(environ)
    paste_adapter = WindowsPasteAdapter()
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
        text_processing=TextProcessingService(
            secret_provider,
            GroqTextProcessingTransportFactory(),
        ),
        clipboard_delivery=ClipboardDeliveryService(WindowsClipboard()),
        auto_paste=AutoPasteService(paste_adapter, wisper_process_id=os.getpid()),
        focus_port=paste_adapter,
        diagnostic_journal=RotatingDiagnosticJournal(logs_dir / "diagnostics.jsonl"),
    )
