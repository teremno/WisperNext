"""Opt-in Groq smoke using synthetic personal speech; no audio or clipboard access.

Only fixture IDs, status, and counts are reported. This checks provider execution
and safety validation, not native-speaker translation quality or speech recognition.
"""

import argparse
import json
from pathlib import Path

from wispernext.bootstrap import build_application_services
from wispernext.infrastructure.config import LanguageCode, Settings

SAMPLES = {
    LanguageCode.ENGLISH: "well I don't know maybe tomorrow can you call me at 10",
    LanguageCode.UKRAINIAN: "ну я не знаю може завтра можеш подзвонити мені о 10",
    LanguageCode.RUSSIAN: "ну я не знаю может завтра можешь позвонить мне в 10",
    LanguageCode.GERMAN: "na ja ich weiß nicht vielleicht morgen kannst du mich um 10 anrufen",
    LanguageCode.FRENCH: "bon je ne sais pas peut-être demain peux-tu m'appeler à 10",
    LanguageCode.SPANISH: "bueno no sé quizá mañana puedes llamarme a las 10",
    LanguageCode.ITALIAN: "beh non lo so forse domani puoi chiamarmi alle 10",
    LanguageCode.PORTUGUESE: "bem não sei talvez amanhã você pode me ligar às 10",
    LanguageCode.POLISH: "no nie wiem może jutro możesz zadzwonić do mnie o 10",
    LanguageCode.DUTCH: "nou ik weet het niet misschien morgen kun je me om 10 bellen",
    LanguageCode.TURKISH: "yani bilmiyorum belki yarın beni saat 10 gibi arayabilir misin",
    LanguageCode.ARABIC: "طيب لا أعرف ربما غدا هل يمكنك الاتصال بي الساعة 10",
    LanguageCode.HINDI: "मुझे नहीं पता शायद कल क्या तुम मुझे 10 बजे फोन कर सकते हो",
    LanguageCode.CHINESE_SIMPLIFIED: "嗯我不知道也许明天你能在10点给我打电话吗",
    LanguageCode.JAPANESE: "ええとわからないたぶん明日10時に電話してくれる",
    LanguageCode.KOREAN: "음 잘 모르겠어요 아마 내일 10시에 전화해 줄 수 있어요",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--format-only", action="store_true")
    modes.add_argument("--translations-only", action="store_true")
    parser.add_argument("--language", choices=[language.value for language in LanguageCode])
    parser.add_argument("--output", type=Path, help="Write only privacy-safe result metadata.")
    arguments = parser.parse_args()
    processor = build_application_services().text_processing
    evidence: list[dict[str, object]] = []
    for language, sample in SAMPLES.items():
        if arguments.language is not None and language.value != arguments.language:
            continue
        modes_to_run = []
        if not arguments.translations_only:
            modes_to_run.append(("format", sample, language, None))
        if not arguments.format_only:
            source_language = (
                LanguageCode.UKRAINIAN if language is LanguageCode.ENGLISH else LanguageCode.ENGLISH
            )
            modes_to_run.append(("translate", SAMPLES[source_language], source_language, language))
        for name, transcript, input_language, output_language in modes_to_run:
            result = processor.process(
                transcript,
                model=Settings().text_model,
                input_language=input_language,
                output_language=output_language,
                safe_formatting=True,
            )
            record: dict[str, object] = {
                "case": f"{name}_{language.value}",
                "accepted": not result.used_fallback,
                "transformed": result.transformed,
                "failure": result.failure.value if result.failure else None,
                "attempts": result.attempts,
            }
            evidence.append(record)
            print(json.dumps(record), flush=True)
    succeeded = all(item["accepted"] for item in evidence)
    payload = {"status": "passed" if succeeded else "failed", "cases": evidence}
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "case_count": len(evidence)}))
    return 0 if succeeded else 2


if __name__ == "__main__":
    raise SystemExit(main())
