"""Windows desktop entry point."""

from wispernext.ui.qt_runtime import run_desktop_application


def main() -> None:
    """Run the single-instance floating desktop application."""
    raise SystemExit(run_desktop_application())


if __name__ == "__main__":
    main()
