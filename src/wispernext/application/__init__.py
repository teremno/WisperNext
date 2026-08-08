"""Application use cases."""

from wispernext.application.controller import DictationController, TaskScheduler
from wispernext.application.delivery import (
    AutoPasteResult,
    AutoPasteService,
    AutoPasteStatus,
    ClipboardAdapterError,
    ClipboardDeliveryResult,
    ClipboardDeliveryService,
    ClipboardDeliveryStatus,
    FocusContext,
    PastePort,
)
from wispernext.application.transcription import (
    ProviderFailureCode,
    TranscriptionFailureCode,
    TranscriptionProviderError,
    TranscriptionResult,
    TranscriptionService,
    TranscriptionTransport,
    TranscriptionTransportFactory,
)

__all__ = [
    "AutoPasteResult",
    "AutoPasteService",
    "AutoPasteStatus",
    "ClipboardAdapterError",
    "ClipboardDeliveryResult",
    "ClipboardDeliveryService",
    "ClipboardDeliveryStatus",
    "DictationController",
    "FocusContext",
    "PastePort",
    "ProviderFailureCode",
    "TaskScheduler",
    "TranscriptionFailureCode",
    "TranscriptionProviderError",
    "TranscriptionResult",
    "TranscriptionService",
    "TranscriptionTransport",
    "TranscriptionTransportFactory",
]
