"""Background orchestration for one complete dictation lifecycle."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from dataclasses import replace
from threading import RLock
from typing import Protocol

from wispernext.application.delivery import (
    AutoPasteService,
    ClipboardDeliveryService,
    FocusContext,
    PastePort,
)
from wispernext.application.transcription import TranscriptionFailureCode, TranscriptionService
from wispernext.audio.catalog import MicrophoneCatalogService
from wispernext.audio.devices import ResolutionStatus
from wispernext.audio.session import AudioSessionError, AudioSessionService
from wispernext.audio.signal import AudioCategory, validate_audio
from wispernext.domain import (
    AppError,
    ApplicationIntent,
    ApplicationState,
    ApplicationStateMachine,
    ErrorCode,
    StateSnapshot,
)
from wispernext.infrastructure.config import JsonSettingsStore, Settings, SettingsStorageError

StateListener = Callable[[StateSnapshot], None]
UiDispatcher = Callable[[Callable[[], None]], None]


class TaskScheduler(Protocol):
    def schedule(self, task: Callable[[], None]) -> None: ...

    def close(self) -> None: ...


class ThreadTaskScheduler:
    """Serialize blocking work away from the UI thread."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="wisper-worker")

    def schedule(self, task: Callable[[], None]) -> None:
        self._executor.submit(task)

    def close(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)


class DictationController:
    """Accept user intents and coordinate services without owning any UI widgets."""

    def __init__(
        self,
        *,
        state_machine: ApplicationStateMachine,
        microphone_catalog: MicrophoneCatalogService,
        audio_session: AudioSessionService,
        transcription: TranscriptionService,
        clipboard_delivery: ClipboardDeliveryService,
        auto_paste: AutoPasteService,
        focus_port: PastePort,
        settings_store: JsonSettingsStore,
        initial_settings: Settings,
        state_listener: StateListener,
        notice_listener: Callable[[str], None],
        ui_dispatcher: UiDispatcher,
        scheduler: TaskScheduler | None = None,
    ) -> None:
        self._state_machine = state_machine
        self._microphone_catalog = microphone_catalog
        self._audio_session = audio_session
        self._transcription = transcription
        self._clipboard_delivery = clipboard_delivery
        self._auto_paste = auto_paste
        self._focus_port = focus_port
        self._settings_store = settings_store
        self._state_listener = state_listener
        self._notice_listener = notice_listener
        self._ui_dispatcher = ui_dispatcher
        self._scheduler = scheduler or ThreadTaskScheduler()
        self._settings = initial_settings
        self._recording_context: FocusContext | None = None
        self._lock = RLock()

    def start(self) -> None:
        """Schedule initialization without blocking the UI thread."""
        self._scheduler.schedule(self._initialize)

    def _initialize(self) -> None:
        with self._lock:
            self._state_machine.transition_to(ApplicationState.IDLE)
            self._emit_locked()

    def save_button_position(self, x: int, y: int) -> None:
        """Persist logical Qt coordinates on the serialized worker."""
        self._scheduler.schedule(lambda: self._save_button_position(x, y))

    def _save_button_position(self, x: int, y: int) -> None:
        with self._lock:
            updated = replace(self._settings, floating_button_x=x, floating_button_y=y)
        try:
            self._settings_store.save(updated)
        except SettingsStorageError:
            self._ui_dispatcher(
                lambda: self._notice_listener("Не вдалося зберегти позицію кнопки.")
            )
            return
        with self._lock:
            self._settings = updated

    def toggle_recording(self) -> None:
        """Handle the same toggle intent from the floating button or global hotkey."""
        with self._lock:
            if self._state_machine.snapshot().state is ApplicationState.RECOVERABLE_ERROR:
                self._state_machine.handle_intent(ApplicationIntent.RETRY)
                self._emit_locked()
                return
            result = self._state_machine.handle_intent(ApplicationIntent.TOGGLE_RECORDING)
            self._emit_locked()
            if not result.accepted:
                return
            if result.current_state is ApplicationState.OPENING_AUDIO:
                self._recording_context = self._focus_port.current_focus()
                self._scheduler.schedule(self._open_audio)
            elif result.current_state is ApplicationState.STOPPING_AUDIO:
                self._scheduler.schedule(self._finish_dictation)

    def shutdown(self) -> None:
        with self._lock:
            result = self._state_machine.handle_intent(ApplicationIntent.SHUTDOWN)
            self._emit_locked()
            if result.accepted:
                self._scheduler.schedule(self._finish_shutdown)

    def close(self) -> None:
        self._scheduler.close()

    def _open_audio(self) -> None:
        try:
            resolution = self._microphone_catalog.resolve(self._settings)
            if resolution.status is not ResolutionStatus.RESOLVED or resolution.device is None:
                self._fail(
                    AppError(
                        ErrorCode.NO_DEVICE,
                        "Не вдалося знайти вибраний мікрофон.",
                        True,
                    )
                )
                return
            self._audio_session.start(resolution.device)
            self._transition(ApplicationState.RECORDING)
        except AudioSessionError:
            self._fail(AppError(ErrorCode.STREAM_ERROR, "Не вдалося запустити мікрофон.", True))
        except Exception:
            self._fail(AppError(ErrorCode.UNEXPECTED, "Не вдалося почати запис.", True))

    def _finish_dictation(self) -> None:
        try:
            audio = self._audio_session.stop()
            self._transition(ApplicationState.VALIDATING_AUDIO)
            validation = validate_audio(audio)
            if validation.category is not AudioCategory.VALID_AUDIO:
                self._fail(_audio_error(validation.category))
                return

            self._transition(ApplicationState.TRANSCRIBING)
            transcription = self._transcription.transcribe(
                audio,
                model=self._settings.transcription_model,
                language=self._settings.input_language,
            )
            if not transcription.succeeded or transcription.text is None:
                self._fail(_transcription_error(transcription.failure))
                return

            self._transition(ApplicationState.DELIVERING_TEXT)
            delivery = self._clipboard_delivery.deliver(transcription.text)
            if not delivery.verified:
                self._fail(
                    AppError(ErrorCode.DELIVERY_FAILED, "Не вдалося перевірити буфер обміну.", True)
                )
                return

            self._transition(ApplicationState.IDLE)
            self._auto_paste.try_paste(
                enabled=self._settings.auto_paste,
                clipboard_delivery=delivery,
                recording_context=self._recording_context,
                application_state=ApplicationState.IDLE,
            )
        except AudioSessionError:
            self._fail(AppError(ErrorCode.STREAM_ERROR, "Не вдалося завершити запис.", True))
        except Exception:
            self._fail(AppError(ErrorCode.UNEXPECTED, "Обробка диктування не вдалася.", True))

    def _finish_shutdown(self) -> None:
        with suppress(AudioSessionError):
            self._audio_session.stop()
        self._transition(ApplicationState.TERMINATED)

    def _transition(self, target: ApplicationState) -> None:
        with self._lock:
            result = self._state_machine.transition_to(target)
            if result.accepted:
                self._emit_locked()

    def _fail(self, error: AppError) -> None:
        with self._lock:
            self._fail_locked(error)

    def _fail_locked(self, error: AppError) -> None:
        self._state_machine.fail(error)
        self._emit_locked()

    def _emit_locked(self) -> None:
        snapshot = self._state_machine.snapshot()
        self._ui_dispatcher(lambda: self._state_listener(snapshot))


def _audio_error(category: AudioCategory) -> AppError:
    mapping = {
        AudioCategory.NO_AUDIO_FRAMES: (ErrorCode.NO_AUDIO_FRAMES, "Мікрофон не передав звук."),
        AudioCategory.TOO_SHORT: (ErrorCode.TOO_SHORT, "Запис надто короткий."),
        AudioCategory.WEAK_SIGNAL: (ErrorCode.WEAK_SIGNAL, "Сигнал мікрофона надто слабкий."),
        AudioCategory.CLIPPED_SIGNAL: (
            ErrorCode.CLIPPED_SIGNAL,
            "Сигнал мікрофона перевантажений.",
        ),
    }
    code, message = mapping.get(category, (ErrorCode.UNEXPECTED, "Аудіо не пройшло перевірку."))
    return AppError(code, message, True)


def _transcription_error(failure: TranscriptionFailureCode | None) -> AppError:
    if failure is TranscriptionFailureCode.MISSING_API_KEY:
        return AppError(ErrorCode.PERMISSION_DENIED, "Groq API-ключ не налаштований.", True)
    if failure in {
        TranscriptionFailureCode.AUTHENTICATION,
        TranscriptionFailureCode.PERMISSION_DENIED,
    }:
        return AppError(ErrorCode.PERMISSION_DENIED, "Groq відхилив API-ключ.", True)
    return AppError(ErrorCode.PROVIDER_UNAVAILABLE, "Groq зараз недоступний.", True)
