import ctypes

from wispernext.platform.windows.clipboard import _INPUT


def test_send_input_structure_matches_win32_abi() -> None:
    expected_size = 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28

    assert ctypes.sizeof(_INPUT) == expected_size
