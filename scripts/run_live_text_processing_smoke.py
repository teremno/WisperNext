"""Opt-in Groq formatting and bidirectional translation smoke test."""

import json

from wispernext.bootstrap import build_application_services
from wispernext.infrastructure.config import LanguageCode, Settings


def main() -> int:
    processor = build_application_services().text_processing
    settings = Settings()
    cases = [
        (
            "format_uk",
            "привіт це короткий тест",
            LanguageCode.UKRAINIAN,
            None,
            True,
        )
    ]
    for output_language in LanguageCode:
        if output_language is LanguageCode.ENGLISH:
            cases.append(
                (
                    "translate_to_en",
                    "Привіт, це короткий тест.",
                    LanguageCode.UKRAINIAN,
                    output_language,
                    False,
                )
            )
        else:
            cases.append(
                (
                    f"translate_to_{output_language.value}",
                    "Hello, this is a short test.",
                    LanguageCode.ENGLISH,
                    output_language,
                    False,
                )
            )
    evidence: list[dict[str, object]] = []
    for name, transcript, input_language, output_language, formatting in cases:
        result = processor.process(
            transcript,
            model=settings.text_model,
            input_language=input_language,
            output_language=output_language,
            safe_formatting=formatting,
        )
        evidence.append(
            {
                "case": name,
                "transformed": result.transformed,
                "used_fallback": result.used_fallback,
                "failure": result.failure.value if result.failure else None,
            }
        )
    succeeded = all(item["transformed"] and not item["used_fallback"] for item in evidence)
    print(json.dumps({"status": "passed" if succeeded else "failed", "cases": evidence}))
    return 0 if succeeded else 2


if __name__ == "__main__":
    raise SystemExit(main())
