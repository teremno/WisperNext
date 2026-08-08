"""Bounded Win32 Unicode clipboard and single-paste adapters."""

import ctypes
from ctypes import wintypes

from wispernext.application.delivery import ClipboardAdapterError, FocusContext

_CF_UNICODETEXT = 13
_GMEM_MOVEABLE = 0x0002
_VK_CONTROL = 0x11
_VK_V = 0x56
_KEYEVENTF_KEYUP = 0x0002
_INPUT_KEYBOARD = 1


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT)]  # noqa: RUF012


class _INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUTUNION)]


class WindowsClipboard:
    """Read or replace Unicode text while holding the clipboard for one short operation."""

    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("User32.dll", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        self._user32.OpenClipboard.argtypes = [wintypes.HWND]
        self._user32.OpenClipboard.restype = wintypes.BOOL
        self._user32.CloseClipboard.argtypes = []
        self._user32.CloseClipboard.restype = wintypes.BOOL
        self._user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
        self._user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
        self._user32.GetClipboardData.argtypes = [wintypes.UINT]
        self._user32.GetClipboardData.restype = wintypes.HANDLE
        self._user32.EmptyClipboard.argtypes = []
        self._user32.EmptyClipboard.restype = wintypes.BOOL
        self._user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        self._user32.SetClipboardData.restype = wintypes.HANDLE
        self._kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        self._kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        self._kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        self._kernel32.GlobalLock.restype = wintypes.LPVOID
        self._kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        self._kernel32.GlobalUnlock.restype = wintypes.BOOL
        self._kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
        self._kernel32.GlobalFree.restype = wintypes.HGLOBAL

    def read_text(self) -> str | None:
        self._open()
        try:
            if not self._user32.IsClipboardFormatAvailable(_CF_UNICODETEXT):
                return None
            handle = self._user32.GetClipboardData(_CF_UNICODETEXT)
            if not handle:
                raise ClipboardAdapterError("Could not read clipboard text.")
            pointer = self._kernel32.GlobalLock(handle)
            if not pointer:
                raise ClipboardAdapterError("Could not lock clipboard text.")
            try:
                return ctypes.wstring_at(pointer)
            finally:
                self._kernel32.GlobalUnlock(handle)
        finally:
            self._user32.CloseClipboard()

    def write_text(self, text: str) -> None:
        encoded = (text + "\0").encode("utf-16-le")
        handle = self._kernel32.GlobalAlloc(_GMEM_MOVEABLE, len(encoded))
        if not handle:
            raise ClipboardAdapterError("Could not allocate clipboard text.")
        transferred = False
        try:
            pointer = self._kernel32.GlobalLock(handle)
            if not pointer:
                raise ClipboardAdapterError("Could not lock clipboard allocation.")
            try:
                ctypes.memmove(pointer, encoded, len(encoded))
            finally:
                self._kernel32.GlobalUnlock(handle)

            self._open()
            try:
                if not self._user32.EmptyClipboard():
                    raise ClipboardAdapterError("Could not prepare the clipboard.")
                if not self._user32.SetClipboardData(_CF_UNICODETEXT, handle):
                    raise ClipboardAdapterError("Could not set clipboard text.")
                transferred = True
            finally:
                self._user32.CloseClipboard()
        finally:
            if not transferred:
                self._kernel32.GlobalFree(handle)

    def _open(self) -> None:
        if not self._user32.OpenClipboard(None):
            raise ClipboardAdapterError("Clipboard is currently unavailable.")


class WindowsPasteAdapter:
    """Inspect foreground ownership and send one Ctrl+V without changing focus."""

    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("User32.dll", use_last_error=True)
        self._user32.GetForegroundWindow.argtypes = []
        self._user32.GetForegroundWindow.restype = wintypes.HWND
        self._user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self._user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self._user32.SendInput.argtypes = [
            wintypes.UINT,
            ctypes.POINTER(_INPUT),
            ctypes.c_int,
        ]
        self._user32.SendInput.restype = wintypes.UINT

    def current_focus(self) -> FocusContext | None:
        window_handle = self._user32.GetForegroundWindow()
        if not window_handle:
            return None
        process_id = wintypes.DWORD()
        thread_id = self._user32.GetWindowThreadProcessId(
            window_handle,
            ctypes.byref(process_id),
        )
        if not thread_id or not process_id.value:
            return None
        return FocusContext(window_handle, process_id.value, thread_id)

    def paste_once(self, expected_window_handle: int) -> bool:
        if self._user32.GetForegroundWindow() != expected_window_handle:
            return False
        inputs = (_INPUT * 4)(
            self._keyboard_input(_VK_CONTROL, 0),
            self._keyboard_input(_VK_V, 0),
            self._keyboard_input(_VK_V, _KEYEVENTF_KEYUP),
            self._keyboard_input(_VK_CONTROL, _KEYEVENTF_KEYUP),
        )
        sent = self._user32.SendInput(len(inputs), inputs, ctypes.sizeof(_INPUT))
        return int(sent) == len(inputs)

    @staticmethod
    def _keyboard_input(key: int, flags: int) -> _INPUT:
        return _INPUT(
            type=_INPUT_KEYBOARD,
            union=_INPUTUNION(
                ki=_KEYBDINPUT(
                    wVk=key,
                    wScan=0,
                    dwFlags=flags,
                    time=0,
                    dwExtraInfo=None,
                )
            ),
        )
