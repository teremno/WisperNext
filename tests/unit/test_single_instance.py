from uuid import uuid4

from wispernext.platform.windows.single_instance import WindowsSingleInstance


def test_named_mutex_allows_exactly_one_primary_owner() -> None:
    name = f"Local\\WisperNext.Test.{uuid4().hex}"
    first = WindowsSingleInstance(name)
    second = WindowsSingleInstance(name)
    try:
        assert first.is_primary
        assert not second.is_primary
    finally:
        second.close()
        first.close()

    replacement = WindowsSingleInstance(name)
    try:
        assert replacement.is_primary
    finally:
        replacement.close()
