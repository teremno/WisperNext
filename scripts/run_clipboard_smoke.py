"""Opt-in Windows clipboard delivery test that restores the original Unicode text."""

import json
from uuid import uuid4

from wispernext.application import ClipboardDeliveryService
from wispernext.platform.windows.clipboard import WindowsClipboard


def main() -> int:
    clipboard = WindowsClipboard()
    original = clipboard.read_text()
    if original is None:
        print(json.dumps({"status": "skipped_non_text_or_empty_clipboard"}))
        return 2

    sentinel = f"WisperNext clipboard smoke {uuid4().hex}"
    delivery = None
    try:
        delivery = ClipboardDeliveryService(clipboard).deliver(sentinel)
    finally:
        clipboard.write_text(original)
        restored = clipboard.read_text() == original

    if delivery is None:
        print(json.dumps({"status": "delivery_failed", "restored": restored}))
        return 3
    succeeded = delivery.verified and restored
    print(
        json.dumps(
            {
                "status": "verified_and_restored" if succeeded else delivery.status.value,
                "delivery_attempts": delivery.attempts,
                "restored": restored,
            }
        )
    )
    return 0 if succeeded else 4


if __name__ == "__main__":
    raise SystemExit(main())
