# ADR 0009: Structured Groq text processing with raw fallback

## Status

Accepted — 2026-08-08

## Context

WisperNext must optionally format a transcript or translate it into one of 15 output languages.
Dictated content is untrusted prompt data, provider output can drift, and optional processing must
never destroy an otherwise valid transcription. The previous configured text-model default is also
scheduled for provider shutdown on 2026-08-16.

## Decision

- Keep transcription and text processing as separate application services and provider adapters.
- Use `openai/gpt-oss-120b` as the migrated text-model default because Groq recommends it as a
  replacement and documents strong multilingual support.
- Send the transcript as a JSON string field, grant no tools, use strict JSON-schema output, cap
  output tokens, use low reasoning effort, and retain bounded SDK timeout/retry settings.
- Request exactly one operation: conservative same-language formatting or translation to one fixed
  output language.
- Validate response shape, language code, wrappers/meta-commentary, length, number preservation,
  and same-language lexical similarity before delivery.
- On any provider or validation failure, deliver the original transcript and show a non-secret
  fallback notice.
- Store no transcript history, response history, API key, or provider error body.

## Consequences

- A valid transcript remains deliverable during formatter outages or suspicious model output.
- The language UI can advertise only the fixed tested set while the schema retains typed codes.
- Conservative validation may reject a legitimate broad correction or unusually expansive
  translation; this intentionally produces the safer raw-transcript fallback.
- Provider language reporting is not an independent language detector, so live multilingual smoke
  coverage and fallback validation remain necessary.
