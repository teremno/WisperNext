"""Minimal Windows Credential Manager adapter using the native Credential API."""

import ctypes
import os
from ctypes import wintypes
from typing import Final

from wispernext.infrastructure.secrets import SecretStorageError

_CRED_TYPE_GENERIC: Final = 1
_CRED_PERSIST_LOCAL_MACHINE: Final = 2
_ERROR_NOT_FOUND: Final = 1168
_USERNAME: Final = "WisperNext"


class _CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class WindowsCredentialStore:
    """User-scoped Generic Credential persistence without external dependencies."""

    def __init__(self) -> None:
        if os.name != "nt":
            raise SecretStorageError("Windows Credential Manager is unavailable.")
        self._advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        self._advapi32.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(_CREDENTIALW)),
        ]
        self._advapi32.CredReadW.restype = wintypes.BOOL
        self._advapi32.CredWriteW.argtypes = [
            ctypes.POINTER(_CREDENTIALW),
            wintypes.DWORD,
        ]
        self._advapi32.CredWriteW.restype = wintypes.BOOL
        self._advapi32.CredDeleteW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        self._advapi32.CredDeleteW.restype = wintypes.BOOL
        self._advapi32.CredFree.argtypes = [ctypes.c_void_p]
        self._advapi32.CredFree.restype = None

    def read(self, target: str) -> bytes | None:
        pointer = ctypes.POINTER(_CREDENTIALW)()
        if not self._advapi32.CredReadW(
            target,
            _CRED_TYPE_GENERIC,
            0,
            ctypes.byref(pointer),
        ):
            error_code = ctypes.get_last_error()
            if error_code == _ERROR_NOT_FOUND:
                return None
            raise SecretStorageError("Could not read the Windows credential.")
        try:
            credential = pointer.contents
            return ctypes.string_at(
                credential.CredentialBlob,
                credential.CredentialBlobSize,
            )
        finally:
            self._advapi32.CredFree(pointer)

    def write(self, target: str, value: bytes) -> None:
        if not value:
            raise ValueError("Credential value must not be empty.")
        blob = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
        credential = _CREDENTIALW()
        credential.Type = _CRED_TYPE_GENERIC
        credential.TargetName = target
        credential.CredentialBlobSize = len(value)
        credential.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
        credential.Persist = _CRED_PERSIST_LOCAL_MACHINE
        credential.UserName = _USERNAME
        if not self._advapi32.CredWriteW(ctypes.byref(credential), 0):
            raise SecretStorageError("Could not write the Windows credential.")

    def delete(self, target: str) -> bool:
        if self._advapi32.CredDeleteW(target, _CRED_TYPE_GENERIC, 0):
            return True
        error_code = ctypes.get_last_error()
        if error_code == _ERROR_NOT_FOUND:
            return False
        raise SecretStorageError("Could not delete the Windows credential.")
