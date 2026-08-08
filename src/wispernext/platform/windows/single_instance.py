"""Single-process ownership through a user-session Win32 named mutex."""

import ctypes
from ctypes import wintypes

_ERROR_ALREADY_EXISTS = 183
_MUTEX_NAME = "Local\\WisperNext.Singleton.v1"


class SingleInstanceError(RuntimeError):
    """Raised when single-instance ownership cannot be determined safely."""


class WindowsSingleInstance:
    """Own one named mutex for the lifetime of the primary application process."""

    def __init__(self, name: str = _MUTEX_NAME) -> None:
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        ctypes.set_last_error(0)
        handle = kernel32.CreateMutexW(None, False, name)
        if not handle:
            raise SingleInstanceError("Could not create the application instance guard.")
        self._kernel32 = kernel32
        self._handle: int | None = int(handle)
        self._primary = ctypes.get_last_error() != _ERROR_ALREADY_EXISTS
        if not self._primary:
            self.close()

    @property
    def is_primary(self) -> bool:
        return self._primary

    def close(self) -> None:
        handle = self._handle
        self._handle = None
        if handle is not None:
            self._kernel32.CloseHandle(handle)

    def __enter__(self) -> "WindowsSingleInstance":
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self.close()
