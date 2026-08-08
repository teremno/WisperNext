# ADR 0005: Groq transcription provider

## Context

The first product slice needs remote speech-to-text while keeping credentials and captured
audio private by default. CI must never contact Groq, and invalid capture must never be uploaded.

## Decision

Use the official `groq` Python SDK with `whisper-large-v3-turbo`. Keep the SDK behind an
application-owned transport protocol and create its client lazily only after audio validation
and secret lookup.

Resample a copy of valid mono audio to 16 kHz and encode it in memory as PCM16 WAV. Upload only
audio categorized as `VALID_AUDIO`; empty, short, weak, and clipped captures stay local. Read the
API key from `WISPER_GROQ_API_KEY`, never from settings, logs, or source control.

Configure a 3-second connect timeout, 15-second read timeout, 10-second write timeout, 20-second
overall timeout, and one SDK retry. Map provider exceptions into privacy-safe internal categories
without storing response bodies, transcripts, or exception text.

## Alternatives considered

- Hand-written HTTP calls: rejected because the official SDK already provides typed errors and
  retry handling.
- Temporary WAV files: rejected because the provider accepts in-memory file tuples.
- Uploading weak audio for best-effort recognition: rejected to avoid unnecessary disclosure and
  cost.
- Unlimited or application-level retries: rejected because dictation must fail promptly and avoid
  duplicate requests.

## Consequences

- Unit tests use fake transports and make zero network calls.
- The key must be present in the launched process environment.
- Provider outages and rate limits produce explicit recoverable failures.
- Transcript text exists only in memory until a later explicit storage or paste feature.

## Verification method

- Unit tests verify validation gating, resampling/WAV shape, one provider call, language mapping,
  timeout/retry configuration, and typed failure mapping.
- CI runs the same tests without a Groq credential.
- One manually authorized live smoke test records only status and audio metrics, not transcript
  content or the API key.
