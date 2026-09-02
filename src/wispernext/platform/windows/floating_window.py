"""Native Windows state for the non-activating floating control."""

import ctypes
from typing import Protocol

_GWL_EXSTYLE = -20
_WS_EX_TOPMOST = 0x00000008
_WS_EX_TOOLWINDOW = 0x00000080
_WS_EX_NOACTIVATE = 0x08000000
_HWND_TOPMOST = -1
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOACTIVATE = 0x0010
_SWP_SHOWWINDOW = 0x0040


class FloatingWindowAdapter(Protocol):
    """Inspect and restore the bounded native state owned by the floating UI."""

    def apply_required_state(self, window_handle: int) -> None:
        """Make the window non-activating, visible, and topmost."""
        ...

    def is_topmost(self, window_handle: int) -> bool:
        """Return whether Windows currently marks the window topmost."""
        ...

    def is_visible(self, window_handle: int) -> bool:
        """Return whether the native window is currently visible."""
        ...


class WindowsFloatingWindowAdapter:
    """Use User32 without changing focus, audio, or broader Windows settings."""

    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("User32.dll", use_last_error=True)
        self._user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self._user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        self._user32.SetWindowLongPtrW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_ssize_t,
        ]
        self._user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        self._user32.SetWindowPos.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        self._user32.SetWindowPos.restype = ctypes.c_bool
        self._user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
        self._user32.IsWindowVisible.restype = ctypes.c_bool

    def apply_required_state(self, window_handle: int) -> None:
        style = self._extended_style(window_handle)
        ctypes.set_last_error(0)
        previous = self._user32.SetWindowLongPtrW(
            window_handle,
            _GWL_EXSTYLE,
            style | _WS_EX_TOOLWINDOW | _WS_EX_NOACTIVATE,
        )
        if previous == 0 and ctypes.get_last_error() != 0:
            raise ctypes.WinError(ctypes.get_last_error())

        restored = self._user32.SetWindowPos(
            window_handle,
            _HWND_TOPMOST,
            0,
            0,
            0,
            0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_SHOWWINDOW,
        )
        if not restored:
            raise ctypes.WinError(ctypes.get_last_error())

    def is_topmost(self, window_handle: int) -> bool:
        return bool(self._extended_style(window_handle) & _WS_EX_TOPMOST)

    def is_visible(self, window_handle: int) -> bool:
        return bool(self._user32.IsWindowVisible(window_handle))

    def _extended_style(self, window_handle: int) -> int:
        ctypes.set_last_error(0)
        style = self._user32.GetWindowLongPtrW(window_handle, _GWL_EXSTYLE)
        if style == 0 and ctypes.get_last_error() != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        return int(style)
