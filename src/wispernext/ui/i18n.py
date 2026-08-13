"""Centralized interface localization and Windows-locale resolution."""

from collections.abc import Mapping
from typing import Final

from wispernext.infrastructure.config import InterfaceLanguage, LanguageCode

SUPPORTED_INTERFACE_LANGUAGES: Final = tuple(InterfaceLanguage)
CONTENT_LANGUAGE_ORDER: Final = tuple(LanguageCode)

_NATIVE_INTERFACE_NAMES: Final[Mapping[InterfaceLanguage, str]] = {
    InterfaceLanguage.ENGLISH: "English",
    InterfaceLanguage.UKRAINIAN: "Українська",
    InterfaceLanguage.RUSSIAN: "Русский",
}

_ENGLISH: Final[dict[str, str]] = {
    "settings.window_title": "WisperNext Settings",
    "settings.title": "SETTINGS",
    "settings.subtitle": "Core dictation options. Windows settings are never changed.",
    "settings.interface_group": "INTERFACE",
    "settings.interface_language": "Interface language:",
    "settings.system_default": "System default (English if unsupported)",
    "settings.microphone_group": "MICROPHONE",
    "settings.microphone_source": "Source:",
    "settings.microphone_accessible": "Microphone selection",
    "settings.microphone_default": "Windows default microphone",
    "settings.refresh": "Refresh list",
    "settings.refresh_accessible": "Refresh microphone list",
    "settings.language_group": "LANGUAGE AND TEXT",
    "settings.input_language": "I speak:",
    "settings.output_language": "Final text:",
    "settings.input_accessible": "Spoken language",
    "settings.output_accessible": "Final text language",
    "settings.input_auto": "Detect automatically",
    "settings.output_same": "Same as spoken language",
    "settings.safe_formatting": "Add safe punctuation and paragraphs",
    "settings.behavior_group": "BEHAVIOR",
    "settings.auto_paste": "Automatically paste recognized text",
    "settings.max_recording": "Maximum recording:",
    "settings.seconds_suffix": " s",
    "settings.launch_button": "Show floating button after launch",
    "settings.status_accessible": "Settings status",
    "settings.loading": "Loading microphone list…",
    "settings.refreshing": "Refreshing microphone list…",
    "settings.saved_microphone_unavailable": "The saved microphone is currently unavailable.",
    "settings.microphones_found": "Microphones found: {count}",
    "settings.save": "Save",
    "settings.cancel": "Cancel",
    "settings.saving": "Saving…",
    "tray.tooltip": "WisperNext — dictation",
    "tray.settings": "Settings…",
    "tray.exit": "Exit WisperNext",
    "button.name": "WisperNext microphone button",
    "button.ready": "Ready. Click to start recording.",
    "button.opening": "Opening microphone.",
    "button.recording": "Recording. Click to stop.",
    "button.processing": "Processing dictation.",
    "button.error": "Error. Click to return.",
    "button.disabled": "WisperNext is shutting down.",
    "notice.microphones_failed": "Could not load the microphone list.",
    "notice.settings_save_failed": "Could not save settings.",
    "notice.button_position_failed": "Could not save the button position.",
    "notice.processing_fallback": "Formatting or translation failed. The original text was used.",
    "notice.hotkey_unavailable": "The global hotkey is in use. The microphone button still works.",
    "notice.diagnostics_unavailable": (
        "Dictation works, but the private diagnostic journal is unavailable."
    ),
    "notice.paste.target_changed": (
        "Text is in the clipboard: the active field changed during processing."
    ),
    "notice.paste.wisper_focus": "Text is in the clipboard: a WisperNext window became active.",
    "notice.paste.input_rejected": "Text is in the clipboard: Windows rejected automatic paste.",
    "notice.paste.target_unavailable": "Text is in the clipboard: the target field is unavailable.",
}

_UKRAINIAN: Final[dict[str, str]] = {
    "settings.window_title": "Налаштування WisperNext",
    "settings.title": "НАЛАШТУВАННЯ",
    "settings.subtitle": "Основні параметри диктування. Налаштування Windows не змінюються.",
    "settings.interface_group": "ІНТЕРФЕЙС",
    "settings.interface_language": "Мова інтерфейсу:",
    "settings.system_default": "Системна (англійська, якщо не підтримується)",
    "settings.microphone_group": "МІКРОФОН",
    "settings.microphone_source": "Джерело:",
    "settings.microphone_accessible": "Вибір мікрофона",
    "settings.microphone_default": "Системний мікрофон за замовчуванням",
    "settings.refresh": "Оновити список",
    "settings.refresh_accessible": "Оновити список мікрофонів",
    "settings.language_group": "МОВА І ТЕКСТ",
    "settings.input_language": "Я говорю:",
    "settings.output_language": "Готовий текст:",
    "settings.input_accessible": "Мова мовлення",
    "settings.output_accessible": "Мова готового тексту",
    "settings.input_auto": "Визначати автоматично",
    "settings.output_same": "Така сама, як мова мовлення",
    "settings.safe_formatting": "Додавати безпечну пунктуацію та абзаци",
    "settings.behavior_group": "ПОВЕДІНКА",
    "settings.auto_paste": "Автоматично вставляти розпізнаний текст",
    "settings.max_recording": "Максимальний запис:",
    "settings.seconds_suffix": " с",
    "settings.launch_button": "Показувати плаваючу кнопку після запуску",
    "settings.status_accessible": "Стан налаштувань",
    "settings.loading": "Завантаження списку мікрофонів…",
    "settings.refreshing": "Оновлення списку мікрофонів…",
    "settings.saved_microphone_unavailable": "Збережений мікрофон зараз недоступний.",
    "settings.microphones_found": "Знайдено мікрофонів: {count}",
    "settings.save": "Зберегти",
    "settings.cancel": "Скасувати",
    "settings.saving": "Збереження…",
    "tray.tooltip": "WisperNext — диктування",
    "tray.settings": "Налаштування…",
    "tray.exit": "Вийти з WisperNext",
    "button.name": "Кнопка мікрофона WisperNext",
    "button.ready": "Готово. Натисніть, щоб почати запис.",
    "button.opening": "Відкриття мікрофона.",
    "button.recording": "Запис. Натисніть, щоб зупинити.",
    "button.processing": "Обробка диктування.",
    "button.error": "Помилка. Натисніть, щоб повернутися.",
    "button.disabled": "WisperNext завершує роботу.",
    "notice.microphones_failed": "Не вдалося отримати список мікрофонів.",
    "notice.settings_save_failed": "Не вдалося зберегти налаштування.",
    "notice.button_position_failed": "Не вдалося зберегти позицію кнопки.",
    "notice.processing_fallback": (
        "Форматування або переклад не вдалися. Використано початковий текст."
    ),
    "notice.hotkey_unavailable": "Глобальна клавіша зайнята. Кнопка мікрофона працює.",
    "notice.diagnostics_unavailable": (
        "Диктування працює, але приватний журнал діагностики недоступний."
    ),
    "notice.paste.target_changed": "Текст у буфері: активне поле змінилося під час обробки.",
    "notice.paste.wisper_focus": "Текст у буфері: активним стало вікно WisperNext.",
    "notice.paste.input_rejected": "Текст у буфері: Windows відхилив автоматичне вставлення.",
    "notice.paste.target_unavailable": "Текст у буфері: цільове поле для вставлення недоступне.",
}

_RUSSIAN: Final[dict[str, str]] = {
    "settings.window_title": "Настройки WisperNext",
    "settings.title": "НАСТРОЙКИ",
    "settings.subtitle": "Основные параметры диктовки. Настройки Windows не изменяются.",
    "settings.interface_group": "ИНТЕРФЕЙС",
    "settings.interface_language": "Язык интерфейса:",
    "settings.system_default": "Системный (английский, если не поддерживается)",
    "settings.microphone_group": "МИКРОФОН",
    "settings.microphone_source": "Источник:",
    "settings.microphone_accessible": "Выбор микрофона",
    "settings.microphone_default": "Системный микрофон по умолчанию",
    "settings.refresh": "Обновить список",
    "settings.refresh_accessible": "Обновить список микрофонов",
    "settings.language_group": "ЯЗЫК И ТЕКСТ",
    "settings.input_language": "Я говорю:",
    "settings.output_language": "Готовый текст:",
    "settings.input_accessible": "Язык речи",
    "settings.output_accessible": "Язык готового текста",
    "settings.input_auto": "Определять автоматически",
    "settings.output_same": "Такой же, как язык речи",
    "settings.safe_formatting": "Добавлять безопасную пунктуацию и абзацы",
    "settings.behavior_group": "ПОВЕДЕНИЕ",
    "settings.auto_paste": "Автоматически вставлять распознанный текст",
    "settings.max_recording": "Максимальная запись:",
    "settings.seconds_suffix": " с",
    "settings.launch_button": "Показывать плавающую кнопку после запуска",
    "settings.status_accessible": "Состояние настроек",
    "settings.loading": "Загрузка списка микрофонов…",
    "settings.refreshing": "Обновление списка микрофонов…",
    "settings.saved_microphone_unavailable": "Сохранённый микрофон сейчас недоступен.",
    "settings.microphones_found": "Найдено микрофонов: {count}",
    "settings.save": "Сохранить",
    "settings.cancel": "Отмена",
    "settings.saving": "Сохранение…",
    "tray.tooltip": "WisperNext — диктовка",
    "tray.settings": "Настройки…",
    "tray.exit": "Выйти из WisperNext",
    "button.name": "Кнопка микрофона WisperNext",
    "button.ready": "Готово. Нажмите, чтобы начать запись.",
    "button.opening": "Открытие микрофона.",
    "button.recording": "Запись. Нажмите, чтобы остановить.",
    "button.processing": "Обработка диктовки.",
    "button.error": "Ошибка. Нажмите, чтобы вернуться.",
    "button.disabled": "WisperNext завершает работу.",
    "notice.microphones_failed": "Не удалось получить список микрофонов.",
    "notice.settings_save_failed": "Не удалось сохранить настройки.",
    "notice.button_position_failed": "Не удалось сохранить положение кнопки.",
    "notice.processing_fallback": (
        "Форматирование или перевод не удались. Использован исходный текст."
    ),
    "notice.hotkey_unavailable": "Глобальная клавиша занята. Кнопка микрофона работает.",
    "notice.diagnostics_unavailable": (
        "Диктовка работает, но приватный журнал диагностики недоступен."
    ),
    "notice.paste.target_changed": "Текст в буфере: активное поле изменилось во время обработки.",
    "notice.paste.wisper_focus": "Текст в буфере: активным стало окно WisperNext.",
    "notice.paste.input_rejected": "Текст в буфере: Windows отклонила автоматическую вставку.",
    "notice.paste.target_unavailable": "Текст в буфере: целевое поле для вставки недоступно.",
}

_LANGUAGE_NAMES: Final[Mapping[InterfaceLanguage, Mapping[LanguageCode, str]]] = {
    InterfaceLanguage.ENGLISH: {
        LanguageCode.ENGLISH: "English",
        LanguageCode.UKRAINIAN: "Ukrainian",
        LanguageCode.RUSSIAN: "Russian",
        LanguageCode.GERMAN: "German",
        LanguageCode.FRENCH: "French",
        LanguageCode.SPANISH: "Spanish",
        LanguageCode.ITALIAN: "Italian",
        LanguageCode.PORTUGUESE: "Portuguese",
        LanguageCode.POLISH: "Polish",
        LanguageCode.DUTCH: "Dutch",
        LanguageCode.TURKISH: "Turkish",
        LanguageCode.ARABIC: "Arabic",
        LanguageCode.HINDI: "Hindi",
        LanguageCode.CHINESE_SIMPLIFIED: "Chinese (Simplified)",
        LanguageCode.JAPANESE: "Japanese",
        LanguageCode.KOREAN: "Korean",
    },
    InterfaceLanguage.UKRAINIAN: {
        LanguageCode.ENGLISH: "Англійська",
        LanguageCode.UKRAINIAN: "Українська",
        LanguageCode.RUSSIAN: "Російська",
        LanguageCode.GERMAN: "Німецька",
        LanguageCode.FRENCH: "Французька",
        LanguageCode.SPANISH: "Іспанська",
        LanguageCode.ITALIAN: "Італійська",
        LanguageCode.PORTUGUESE: "Португальська",
        LanguageCode.POLISH: "Польська",
        LanguageCode.DUTCH: "Нідерландська",
        LanguageCode.TURKISH: "Турецька",
        LanguageCode.ARABIC: "Арабська",
        LanguageCode.HINDI: "Гінді",
        LanguageCode.CHINESE_SIMPLIFIED: "Китайська (спрощена)",
        LanguageCode.JAPANESE: "Японська",
        LanguageCode.KOREAN: "Корейська",
    },
    InterfaceLanguage.RUSSIAN: {
        LanguageCode.ENGLISH: "Английский",
        LanguageCode.UKRAINIAN: "Украинский",
        LanguageCode.RUSSIAN: "Русский",
        LanguageCode.GERMAN: "Немецкий",
        LanguageCode.FRENCH: "Французский",
        LanguageCode.SPANISH: "Испанский",
        LanguageCode.ITALIAN: "Итальянский",
        LanguageCode.PORTUGUESE: "Португальский",
        LanguageCode.POLISH: "Польский",
        LanguageCode.DUTCH: "Нидерландский",
        LanguageCode.TURKISH: "Турецкий",
        LanguageCode.ARABIC: "Арабский",
        LanguageCode.HINDI: "Хинди",
        LanguageCode.CHINESE_SIMPLIFIED: "Китайский (упрощённый)",
        LanguageCode.JAPANESE: "Японский",
        LanguageCode.KOREAN: "Корейский",
    },
}

_CATALOGS: Final[Mapping[InterfaceLanguage, Mapping[str, str]]] = {
    InterfaceLanguage.ENGLISH: _ENGLISH,
    InterfaceLanguage.UKRAINIAN: _UKRAINIAN,
    InterfaceLanguage.RUSSIAN: _RUSSIAN,
}


def resolve_interface_language(
    configured: InterfaceLanguage | None,
    system_locale_name: str,
) -> InterfaceLanguage:
    """Resolve a manual preference or supported Windows locale, defaulting to English."""
    if configured is not None:
        return configured
    language_code = system_locale_name.replace("-", "_").split("_", 1)[0].casefold()
    try:
        return InterfaceLanguage(language_code)
    except ValueError:
        return InterfaceLanguage.ENGLISH


def interface_language_options() -> tuple[tuple[str, InterfaceLanguage], ...]:
    """Return stable, self-identifying manual interface-language choices."""
    return tuple((name, language) for language, name in _NATIVE_INTERFACE_NAMES.items())


def language_name(interface_language: InterfaceLanguage, language: LanguageCode) -> str:
    """Return a content-language name in the selected interface language."""
    return _LANGUAGE_NAMES[interface_language][language]


def tr(interface_language: InterfaceLanguage, key: str, **values: object) -> str:
    """Translate one required interface key and interpolate bounded UI values."""
    return _CATALOGS[interface_language][key].format(**values)


def catalogs() -> Mapping[InterfaceLanguage, Mapping[str, str]]:
    """Expose immutable-by-contract catalogs for completeness tests."""
    return _CATALOGS
