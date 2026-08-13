import pytest

from wispernext.infrastructure.config import InterfaceLanguage, LanguageCode
from wispernext.ui.i18n import (
    catalogs,
    interface_language_options,
    language_name,
    resolve_interface_language,
    tr,
)


@pytest.mark.parametrize(
    ("locale_name", "expected"),
    [
        ("en_US", InterfaceLanguage.ENGLISH),
        ("uk_UA", InterfaceLanguage.UKRAINIAN),
        ("ru-RU", InterfaceLanguage.RUSSIAN),
        ("zh_CN", InterfaceLanguage.ENGLISH),
        ("de_DE", InterfaceLanguage.ENGLISH),
        ("", InterfaceLanguage.ENGLISH),
    ],
)
def test_system_locale_resolution_has_english_fallback(
    locale_name: str, expected: InterfaceLanguage
) -> None:
    assert resolve_interface_language(None, locale_name) is expected


def test_manual_interface_language_overrides_windows_locale() -> None:
    assert (
        resolve_interface_language(InterfaceLanguage.RUSSIAN, "uk_UA") is InterfaceLanguage.RUSSIAN
    )


def test_every_catalog_has_the_same_complete_key_set() -> None:
    available = catalogs()
    english_keys = set(available[InterfaceLanguage.ENGLISH])

    assert set(available) == set(InterfaceLanguage)
    assert english_keys
    assert all(set(catalog) == english_keys for catalog in available.values())


def test_every_content_language_has_a_name_in_every_interface_language() -> None:
    for interface_language in InterfaceLanguage:
        assert {
            language_name(interface_language, content_language) for content_language in LanguageCode
        }
        assert len(
            {
                language_name(interface_language, content_language)
                for content_language in LanguageCode
            }
        ) == len(LanguageCode)


def test_interface_options_are_self_identifying_and_russian_is_translated() -> None:
    assert {language for _label, language in interface_language_options()} == set(InterfaceLanguage)
    assert tr(InterfaceLanguage.RUSSIAN, "tray.settings") == "Настройки…"
