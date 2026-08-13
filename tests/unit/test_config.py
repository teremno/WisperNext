import json
from pathlib import Path

import pytest

from wispernext.domain import MicrophoneSelectionMode
from wispernext.infrastructure.config import (
    CURRENT_SCHEMA_VERSION,
    InterfaceLanguage,
    JsonSettingsStore,
    LanguageCode,
    Settings,
    SettingsStorageError,
    SettingsValidationError,
    decode_settings,
    encode_settings,
)


def test_settings_round_trip_preserves_typed_values(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    store = JsonSettingsStore(path)
    expected = Settings(
        microphone_selection_mode=MicrophoneSelectionMode.MANUAL,
        selected_microphone_id="endpoint-123",
        hotkey="Ctrl+F8",
        auto_paste=True,
        floating_button_x=-320,
        floating_button_y=180,
        max_recording_seconds=120,
        interface_language=InterfaceLanguage.RUSSIAN,
        input_language=LanguageCode.UKRAINIAN,
        output_language=LanguageCode.ENGLISH,
    )

    store.save(expected)
    result = store.load()

    assert result.settings == expected
    assert not result.recovered_from_invalid
    assert json.loads(path.read_text(encoding="utf-8")) == encode_settings(expected)


def test_missing_settings_returns_safe_defaults_without_creating_file(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"

    result = JsonSettingsStore(path).load()

    assert result.settings == Settings()
    assert not result.recovered_from_invalid
    assert not path.exists()


def test_versionless_settings_are_migrated_with_current_defaults() -> None:
    migrated = decode_settings({"hotkey": "F9", "auto_paste": True})

    assert migrated.schema_version == CURRENT_SCHEMA_VERSION
    assert migrated.hotkey == "F9"
    assert migrated.auto_paste
    assert migrated.autostart is False
    assert migrated.microphone_selection_mode is MicrophoneSelectionMode.SYSTEM_DEFAULT


def test_version_one_manual_microphone_is_migrated_without_losing_preference() -> None:
    payload = encode_settings(
        Settings(
            microphone_selection_mode=MicrophoneSelectionMode.MANUAL,
            selected_microphone_id="metadata:v1:abc",
        )
    )
    payload["schema_version"] = 1
    payload.pop("microphone_selection_mode")
    payload.pop("floating_button_x")
    payload.pop("floating_button_y")
    payload.pop("interface_language")

    migrated = decode_settings(payload)

    assert migrated.schema_version == CURRENT_SCHEMA_VERSION
    assert migrated.microphone_selection_mode is MicrophoneSelectionMode.MANUAL
    assert migrated.selected_microphone_id == "metadata:v1:abc"


def test_version_two_settings_migrate_with_unset_button_position() -> None:
    payload = encode_settings(Settings())
    payload["schema_version"] = 2
    payload.pop("floating_button_x")
    payload.pop("floating_button_y")
    payload.pop("interface_language")

    migrated = decode_settings(payload)

    assert migrated.schema_version == CURRENT_SCHEMA_VERSION
    assert migrated.floating_button_x is None
    assert migrated.floating_button_y is None


def test_version_three_settings_migrate_deprecated_default_text_model() -> None:
    payload = encode_settings(Settings())
    payload["schema_version"] = 3
    payload["text_model"] = "llama-3.3-70b-versatile"
    payload.pop("interface_language")

    migrated = decode_settings(payload)

    assert migrated.schema_version == CURRENT_SCHEMA_VERSION
    assert migrated.text_model == "openai/gpt-oss-120b"


def test_version_four_settings_migrate_to_system_interface_language() -> None:
    payload = encode_settings(Settings(output_language=LanguageCode.RUSSIAN))
    payload["schema_version"] = 4
    payload.pop("interface_language")

    migrated = decode_settings(payload)

    assert migrated.schema_version == CURRENT_SCHEMA_VERSION
    assert migrated.interface_language is None
    assert migrated.output_language is LanguageCode.RUSSIAN


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"schema_version": True},
        {"schema_version": 999},
        {"schema_version": CURRENT_SCHEMA_VERSION},
        {"unknown": "field"},
        {"auto_paste": 1},
        {"max_recording_seconds": True},
        {"max_recording_seconds": 4},
        {"max_recording_seconds": 1_801},
        {"input_language": "xx"},
        {**encode_settings(Settings()), "interface_language": "xx"},
        {"hotkey": ""},
        {**encode_settings(Settings()), "hotkey": "A"},
        {**encode_settings(Settings()), "hotkey": "7"},
        {**encode_settings(Settings()), "hotkey": "/"},
        {**encode_settings(Settings()), "floating_button_x": 10},
        {**encode_settings(Settings()), "floating_button_x": True, "floating_button_y": 10},
        {
            **encode_settings(Settings()),
            "microphone_selection_mode": MicrophoneSelectionMode.MANUAL.value,
        },
        {
            **encode_settings(Settings()),
            "selected_microphone_id": "metadata:v1:abc",
        },
    ],
)
def test_invalid_settings_are_rejected(payload: object) -> None:
    with pytest.raises(SettingsValidationError):
        decode_settings(payload)


def test_invalid_file_is_preserved_before_defaults_are_returned(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    invalid_content = '{"schema_version": 1, "api_key": "must-not-be-here"}'
    path.write_text(invalid_content, encoding="utf-8")

    result = JsonSettingsStore(path).load()

    assert result.settings == Settings()
    assert result.recovered_from_invalid
    assert result.preserved_invalid_path is not None
    assert result.preserved_invalid_path.read_text(encoding="utf-8") == invalid_content
    assert not path.exists()


def test_save_replaces_existing_file_and_leaves_no_temporary_file(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    store = JsonSettingsStore(path)
    store.save(Settings(hotkey="F8"))

    store.save(Settings(hotkey="F10"))

    assert store.load().settings.hotkey == "F10"
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_replace_failure_preserves_previous_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "settings.json"
    store = JsonSettingsStore(path)
    store.save(Settings(hotkey="F8"))
    original = path.read_bytes()

    def fail_replace(_source: object, _target: object) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr("wispernext.infrastructure.config.os.replace", fail_replace)

    with pytest.raises(SettingsStorageError):
        store.save(Settings(hotkey="F9"))

    assert path.read_bytes() == original
    assert list(tmp_path.glob("*.tmp")) == []


def test_encoded_settings_have_no_secret_field_or_value() -> None:
    encoded = json.dumps(encode_settings(Settings()))

    assert "api_key" not in encoded.lower()
    assert "WISPER_GROQ_API_KEY" not in encoded


def test_settings_schema_contains_all_required_languages() -> None:
    assert {language.value for language in LanguageCode} == {
        "en",
        "uk",
        "ru",
        "de",
        "fr",
        "es",
        "it",
        "pt",
        "pl",
        "nl",
        "tr",
        "ar",
        "hi",
        "zh-CN",
        "ja",
        "ko",
    }
