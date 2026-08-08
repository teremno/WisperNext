"""Application use cases."""

from wispernext.application.delivery import (
    AutoPasteResult,
    AutoPasteService,
    AutoPasteStatus,
    ClipboardAdapterError,
    ClipboardDeliveryResult,
    ClipboardDeliveryService,
    ClipboardDeliveryStatus,
    FocusContext,
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
    "FocusContext",
    "ProviderFailureCode",
    "TranscriptionFailureCode",
    "TranscriptionProviderError",
    "TranscriptionResult",
    "TranscriptionService",
    "TranscriptionTransport",
    "TranscriptionTransportFactory",
]
