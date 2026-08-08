from wispernext import __version__
from wispernext.ui.qt_runtime import HotkeyEventFilter


def test_package_version_is_defined() -> None:
    assert __version__ == "0.0.1"


def test_desktop_runtime_imports_on_supported_python() -> None:
    assert HotkeyEventFilter is not None
