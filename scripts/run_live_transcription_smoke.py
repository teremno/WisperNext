"""Opt-in Windows microphone plus Groq smoke test with privacy-safe output."""

import argparse
import json
import time
import winsound

from wispernext.bootstrap import build_application_services
from wispernext.domain import MicrophoneSelectionMode
from wispernext.infrastructure.config import Settings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--microphone-id")
    args = parser.parse_args()
    if not 1.0 <= args.seconds <= 30.0:
        parser.error("--seconds must be between 1 and 30")

    services = build_application_services()
    settings = (
        Settings(
            microphone_selection_mode=MicrophoneSelectionMode.MANUAL,
            selected_microphone_id=args.microphone_id,
        )
        if args.microphone_id
        else Settings()
    )
    resolution = services.microphone_catalog.resolve(settings)
    if resolution.device is None:
        print(json.dumps({"status": "device_not_resolved", "reason": resolution.status.value}))
        return 2

    device = resolution.device
    winsound.Beep(880, 250)
    services.audio_session.start(device)
    try:
        time.sleep(args.seconds)
    finally:
        audio = services.audio_session.stop()

    result = services.transcription.transcribe(
        audio,
        model=settings.transcription_model,
        language=settings.input_language,
    )
    metrics = result.validation.metrics
    print(
        json.dumps(
            {
                "status": "success" if result.succeeded else "failure",
                "failure": result.failure.value if result.failure else None,
                "device_name": device.name,
                "device_stable_id": device.stable_id,
                "duration_seconds": round(metrics.duration_seconds, 3),
                "rms": round(metrics.rms, 8),
                "peak": round(metrics.peak, 8),
                "clipping_ratio": round(metrics.clipping_ratio, 8),
                "audio_category": result.validation.category.value,
                "transcript_characters": len(result.text) if result.text is not None else 0,
            },
            ensure_ascii=False,
        )
    )
    return 0 if result.succeeded else 3


if __name__ == "__main__":
    raise SystemExit(main())
