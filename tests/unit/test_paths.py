from pathlib import Path

from wispernext.infrastructure.paths import UserPaths


def test_user_paths_use_local_app_data_without_creating_directories(tmp_path: Path) -> None:
    base = tmp_path / "LocalAppData"

    paths = UserPaths.resolve({"LOCALAPPDATA": str(base)})

    assert paths.data_dir == base / "WisperNext"
    assert paths.settings_file == base / "WisperNext" / "settings.json"
    assert paths.logs_dir == base / "WisperNext" / "logs"
    assert not paths.data_dir.exists()


def test_user_paths_have_windows_style_fallback(tmp_path: Path) -> None:
    paths = UserPaths.resolve({}, home=tmp_path)

    assert paths.data_dir == tmp_path / "AppData" / "Local" / "WisperNext"
