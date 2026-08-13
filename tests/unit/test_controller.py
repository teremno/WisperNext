from collections.abc import Callable

from wispernext.application import (
    ClipboardDeliveryResult,
    ClipboardDeliveryStatus,
    DiagnosticEvent,
    DictationController,
    FocusContext,
    TextProcessingFailureCode,
    TextProcessingResult,
    TranscriptionResult,
)
from wispernext.application.delivery import AutoPasteResult, AutoPasteStatus
from wispernext.audio.devices import (
    ConnectionKind,
    DeviceResolution,
    InputDevice,
    ResolutionStatus,
)
from wispernext.audio.signal import CapturedAudio, validate_audio
from wispernext.domain import ApplicationState, ApplicationStateMachine
from wispernext.infrastructure.config import LanguageCode, Settings, SettingsLoadResult


class ImmediateScheduler:
    def schedule(self, task: Callable[[], None]) -> None:
        task()

    def close(self) -> None:
        pass


class QueuedScheduler:
    def __init__(self) -> None:
        self.tasks: list[Callable[[], None]] = []

    def schedule(self, task: Callable[[], None]) -> None:
        self.tasks.append(task)

    def close(self) -> None:
        self.tasks.clear()


class FakeSettingsStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.saved: list[Settings] = []

    def load(self) -> SettingsLoadResult:
        return SettingsLoadResult(self.settings)

    def save(self, settings: Settings) -> None:
        self.saved.append(settings)


DEVICE = InputDevice(
    1,
    "stable",
    "Mic",
    "WASAPI",
    48_000,
    1,
    ConnectionKind.INTERNAL,
)


class FakeCatalog:
    def list_devices(self) -> tuple[InputDevice, ...]:
        return (DEVICE,)

    def resolve(self, _settings: Settings) -> DeviceResolution:
        return DeviceResolution(ResolutionStatus.RESOLVED, DEVICE)


def valid_audio() -> CapturedAudio:
    return CapturedAudio(tuple(0.1 if index % 2 else -0.1 for index in range(48_000)), 48_000)


class FakeAudioSession:
    def __init__(self, captured: CapturedAudio | None = None) -> None:
        self.captured = captured or valid_audio()
        self.start_count = 0
        self.stop_count = 0

    def start(self, _device: InputDevice) -> None:
        self.start_count += 1

    def stop(self) -> CapturedAudio:
        self.stop_count += 1
        return self.captured


class FakeTranscription:
    def __init__(self) -> None:
        self.call_count = 0

    def transcribe(
        self, audio: CapturedAudio, *, model: str, language: object
    ) -> TranscriptionResult:
        self.call_count += 1
        return TranscriptionResult("recognized", None, validate_audio(audio))


class FakeClipboardDelivery:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def deliver(self, text: str) -> ClipboardDeliveryResult:
        self.texts.append(text)
        return ClipboardDeliveryResult(ClipboardDeliveryStatus.VERIFIED, 1, False)


class FakePastePort:
    def __init__(self) -> None:
        self.context = FocusContext(10, 20, 30)

    def current_focus(self) -> FocusContext:
        return self.context

    def paste_once(self, _expected_window_handle: int) -> bool:
        return True


class FakeAutoPaste:
    def __init__(self, status: AutoPasteStatus = AutoPasteStatus.PASTED) -> None:
        self.call_count = 0
        self.status = status

    def try_paste(self, **_kwargs: object) -> AutoPasteResult:
        self.call_count += 1
        return AutoPasteResult(self.status)


class FakeTextProcessing:
    def __init__(self, result: TextProcessingResult | None = None) -> None:
        self.result = result
        self.call_count = 0

    def process(self, transcript: str, **_kwargs: object) -> TextProcessingResult:
        self.call_count += 1
        return self.result or TextProcessingResult(transcript, False, False)


class FakeDiagnosticJournal:
    def __init__(self, succeeds: bool = True) -> None:
        self.succeeds = succeeds
        self.events: list[DiagnosticEvent] = []

    def record(self, event: DiagnosticEvent) -> bool:
        self.events.append(event)
        return self.succeeds


def build_controller(
    *,
    scheduler: ImmediateScheduler | QueuedScheduler,
    audio: FakeAudioSession | None = None,
    settings: Settings | None = None,
    text_processing: FakeTextProcessing | None = None,
    auto_paste: FakeAutoPaste | None = None,
    notices: list[str] | None = None,
    diagnostic_journal: FakeDiagnosticJournal | None = None,
) -> tuple[
    DictationController,
    ApplicationStateMachine,
    FakeAudioSession,
    FakeTranscription,
    FakeClipboardDelivery,
    FakeSettingsStore,
    list[ApplicationState],
]:
    machine = ApplicationStateMachine()
    audio_session = audio or FakeAudioSession()
    transcription = FakeTranscription()
    clipboard = FakeClipboardDelivery()
    initial_settings = settings or Settings()
    settings_store = FakeSettingsStore(initial_settings)
    states: list[ApplicationState] = []
    controller = DictationController(
        state_machine=machine,
        microphone_catalog=FakeCatalog(),  # type: ignore[arg-type]
        audio_session=audio_session,  # type: ignore[arg-type]
        transcription=transcription,  # type: ignore[arg-type]
        text_processing=text_processing or FakeTextProcessing(),  # type: ignore[arg-type]
        clipboard_delivery=clipboard,  # type: ignore[arg-type]
        auto_paste=auto_paste or FakeAutoPaste(),  # type: ignore[arg-type]
        focus_port=FakePastePort(),
        settings_store=settings_store,  # type: ignore[arg-type]
        initial_settings=initial_settings,
        state_listener=lambda snapshot: states.append(snapshot.state),
        notice_listener=(notices if notices is not None else []).append,
        ui_dispatcher=lambda callback: callback(),
        scheduler=scheduler,
        diagnostic_journal=diagnostic_journal,
    )
    return (
        controller,
        machine,
        audio_session,
        transcription,
        clipboard,
        settings_store,
        states,
    )


def test_complete_toggle_workflow_records_transcribes_delivers_and_returns_idle() -> None:
    controller, machine, audio, transcription, clipboard, _store, states = build_controller(
        scheduler=ImmediateScheduler()
    )
    controller.start()

    controller.toggle_recording()
    controller.toggle_recording()

    assert machine.snapshot().state is ApplicationState.IDLE
    assert audio.start_count == 1
    assert audio.stop_count == 1
    assert transcription.call_count == 1
    assert clipboard.texts == ["recognized"]
    assert states == [
        ApplicationState.IDLE,
        ApplicationState.OPENING_AUDIO,
        ApplicationState.RECORDING,
        ApplicationState.STOPPING_AUDIO,
        ApplicationState.VALIDATING_AUDIO,
        ApplicationState.TRANSCRIBING,
        ApplicationState.FORMATTING_OR_TRANSLATING,
        ApplicationState.DELIVERING_TEXT,
        ApplicationState.IDLE,
    ]


def test_duplicate_toggle_while_opening_does_not_schedule_parallel_work() -> None:
    scheduler = QueuedScheduler()
    controller, machine, *_rest = build_controller(scheduler=scheduler)
    controller.start()
    scheduler.tasks.pop(0)()

    controller.toggle_recording()
    controller.toggle_recording()

    assert machine.snapshot().state is ApplicationState.OPENING_AUDIO
    assert len(scheduler.tasks) == 1


def test_invalid_audio_stops_before_groq_and_enters_recoverable_error() -> None:
    weak = CapturedAudio((0.0001,) * 48_000, 48_000)
    controller, machine, _audio, transcription, clipboard, *_rest = build_controller(
        scheduler=ImmediateScheduler(),
        audio=FakeAudioSession(weak),
    )
    controller.start()

    controller.toggle_recording()
    controller.toggle_recording()

    assert machine.snapshot().state is ApplicationState.RECOVERABLE_ERROR
    assert transcription.call_count == 0
    assert clipboard.texts == []


def test_translated_text_is_delivered_after_processing_state() -> None:
    processor = FakeTextProcessing(TextProcessingResult("Hello.", True, False))
    controller, machine, _audio, _transcription, clipboard, *_rest = build_controller(
        scheduler=ImmediateScheduler(),
        settings=Settings(
            input_language=LanguageCode.UKRAINIAN,
            output_language=LanguageCode.ENGLISH,
        ),
        text_processing=processor,
    )
    controller.start()

    controller.toggle_recording()
    controller.toggle_recording()

    assert machine.snapshot().state is ApplicationState.IDLE
    assert processor.call_count == 1
    assert clipboard.texts == ["Hello."]


def test_auto_paste_rejection_surfaces_notice_after_clipboard_delivery() -> None:
    notices: list[str] = []
    controller, machine, _audio, _transcription, clipboard, *_rest = build_controller(
        scheduler=ImmediateScheduler(),
        settings=Settings(auto_paste=True),
        auto_paste=FakeAutoPaste(AutoPasteStatus.INPUT_REJECTED),
        notices=notices,
    )
    controller.start()

    controller.toggle_recording()
    controller.toggle_recording()

    assert machine.snapshot().state is ApplicationState.IDLE
    assert clipboard.texts == ["recognized"]
    assert notices == ["notice.paste.input_rejected"]


def test_processing_failure_delivers_raw_transcript_and_surfaces_fallback() -> None:
    notices: list[str] = []
    processor = FakeTextProcessing(
        TextProcessingResult(
            "recognized",
            False,
            True,
            TextProcessingFailureCode.TIMEOUT,
        )
    )
    controller, _machine, _audio, _transcription, clipboard, *_rest = build_controller(
        scheduler=ImmediateScheduler(),
        text_processing=processor,
        notices=notices,
    )
    controller.start()

    controller.toggle_recording()
    controller.toggle_recording()

    assert clipboard.texts == ["recognized"]
    assert notices == ["notice.processing_fallback"]


def test_processing_and_completion_share_one_private_diagnostic_operation_id() -> None:
    journal = FakeDiagnosticJournal()
    controller, *_rest = build_controller(
        scheduler=ImmediateScheduler(),
        settings=Settings(
            input_language=LanguageCode.UKRAINIAN,
            output_language=LanguageCode.RUSSIAN,
        ),
        text_processing=FakeTextProcessing(
            TextProcessingResult("Переведено.", True, False, attempts=2)
        ),
        diagnostic_journal=journal,
    )
    controller.start()

    controller.toggle_recording()
    controller.toggle_recording()

    assert [event.name.value for event in journal.events] == [
        "text_processing",
        "dictation_complete",
    ]
    assert len({event.operation_id for event in journal.events}) == 1
    assert journal.events[0].input_language == "uk"
    assert journal.events[0].output_language == "ru"
    assert journal.events[0].attempts == 2


def test_unavailable_journal_warns_once_without_stopping_dictation() -> None:
    notices: list[str] = []
    journal = FakeDiagnosticJournal(succeeds=False)
    controller, machine, *_rest = build_controller(
        scheduler=ImmediateScheduler(),
        notices=notices,
        diagnostic_journal=journal,
    )
    controller.start()

    controller.toggle_recording()
    controller.toggle_recording()

    assert machine.snapshot().state is ApplicationState.IDLE
    assert notices.count("notice.diagnostics_unavailable") == 1


def test_button_position_is_saved_on_worker_without_changing_domain_state() -> None:
    controller, machine, _audio, _transcription, _clipboard, store, _states = build_controller(
        scheduler=ImmediateScheduler()
    )
    controller.start()

    controller.save_button_position(-200, 300)

    assert machine.snapshot().state is ApplicationState.IDLE
    assert store.saved[-1].floating_button_x == -200
    assert store.saved[-1].floating_button_y == 300


def test_settings_update_is_persisted_and_used_as_current_snapshot() -> None:
    controller, _machine, _audio, _transcription, _clipboard, store, _states = build_controller(
        scheduler=ImmediateScheduler()
    )
    updated = Settings(auto_paste=True, max_recording_seconds=90)
    saved: list[Settings] = []

    controller.update_settings(updated, saved.append, lambda message: None)

    assert store.saved[-1] == updated
    assert saved == [updated]
    assert controller.current_settings() == updated


def test_microphone_refresh_returns_metadata_without_opening_audio() -> None:
    controller, _machine, audio, *_rest = build_controller(scheduler=ImmediateScheduler())
    loaded: list[tuple[InputDevice, ...]] = []

    controller.request_microphones(loaded.append, lambda message: None)

    assert loaded == [(DEVICE,)]
    assert audio.start_count == 0


def test_shutdown_releases_audio_and_reaches_terminated() -> None:
    controller, machine, audio, *_rest = build_controller(scheduler=ImmediateScheduler())
    controller.start()

    controller.shutdown()

    assert machine.snapshot().state is ApplicationState.TERMINATED
    assert audio.stop_count == 1
