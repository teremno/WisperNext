"""Win32 RegisterHotKey adapter with no keyboard hook."""

import ctypes
from ctypes import wintypes

from wispernext.domain import HotkeyModifier, HotkeySpec

_WM_HOTKEY = 0x0312
_HOTKEY_ID = 0x5753
_MOD_NOREPEAT = 0x4000
_MODIFIER_FLAGS = {
    HotkeyModifier.ALT: 0x0001,
    HotkeyModifier.CTRL: 0x0002,
    HotkeyModifier.SHIFT: 0x0004,
    HotkeyModifier.WIN: 0x0008,
}
_NAMED_VIRTUAL_KEYS = {
    "Pause": 0x13,
    "Insert": 0x2D,
    "Home": 0x24,
    "End": 0x23,
    "PageUp": 0x21,
    "PageDown": 0x22,
    "ScrollLock": 0x91,
    "NumpadAdd": 0x6B,
    "NumpadSubtract": 0x6D,
    "NumpadMultiply": 0x6A,
    "NumpadDivide": 0x6F,
    "NumpadDecimal": 0x6E,
    "MediaPlayPause": 0xB3,
    "MediaNextTrack": 0xB0,
    "MediaPrevTrack": 0xB1,
    "VolumeMute": 0xAD,
    "VolumeUp": 0xAF,
    "VolumeDown": 0xAE,
}


class HotkeyRegistrationError(RuntimeError):
    """Raised when Windows rejects the configured global hotkey."""


class _POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", _POINT),
    ]


class WindowsGlobalHotkey:
    """Register exactly one no-repeat system hotkey and release it deterministically."""

    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("User32.dll", use_last_error=True)
        self._user32.RegisterHotKey.argtypes = [
            wintypes.HWND,
            ctypes.c_int,
            wintypes.UINT,
            wintypes.UINT,
        ]
        self._user32.RegisterHotKey.restype = wintypes.BOOL
        self._user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self._user32.UnregisterHotKey.restype = wintypes.BOOL
        self._registered = False

    def register(self, hotkey: HotkeySpec) -> None:
        self.unregister()
        modifiers = _MOD_NOREPEAT
        for modifier in hotkey.modifiers:
            modifiers |= _MODIFIER_FLAGS[modifier]
        virtual_key = _virtual_key(hotkey.key)
        if not self._user32.RegisterHotKey(None, _HOTKEY_ID, modifiers, virtual_key):
            raise HotkeyRegistrationError("The configured global hotkey is unavailable.")
        self._registered = True

    def unregister(self) -> None:
        if self._registered:
            self._user32.UnregisterHotKey(None, _HOTKEY_ID)
            self._registered = False

    def close(self) -> None:
        self.unregister()


def is_registered_hotkey_message(message_address: int) -> bool:
    """Return whether one native Qt dispatcher message belongs to Wisper's hotkey."""
    if not message_address:
        return False
    message = ctypes.cast(message_address, ctypes.POINTER(_MSG)).contents
    return message.message == _WM_HOTKEY and int(message.wParam) == _HOTKEY_ID


def _virtual_key(key: str) -> int:
    if len(key) == 1 and key.isascii() and key.isalnum():
        return ord(key)
    if key.startswith("F") and key[1:].isdigit():
        return 0x70 + int(key[1:]) - 1
    if key.startswith("Numpad") and key[6:].isdigit():
        return 0x60 + int(key[6:])
    return _NAMED_VIRTUAL_KEYS[key]
