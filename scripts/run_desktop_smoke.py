"""Launch the real desktop composition briefly without triggering dictation."""

import json

from wispernext.ui.qt_runtime import run_desktop_application


def main() -> int:
    exit_code = run_desktop_application(["wispernext-smoke"], exit_after_ms=1_500)
    print(json.dumps({"status": "desktop_started_and_closed", "exit_code": exit_code}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
