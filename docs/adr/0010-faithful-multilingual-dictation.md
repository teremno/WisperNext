# ADR 0010: Faithful multilingual dictation

Date: 2026-10-10. Status: implemented locally.

## Context

The speaker uses dictation as an accessibility tool. Optional postprocessing must preserve
their authorship. Broad prose rewriting and a permissive similarity threshold can lose
negation, uncertainty, repetition, and personal phrasing.

## Decision

- Adapt Humanizer v3.1.0 into the existing Groq prompt for all 16 configured languages.
- Also draw on stasiiakondratiuk/humanizer (MIT, commit `7662e521`): preserve author voice
  and avoid adding bureaucratic or formulaic phrasing in Ukrainian, Russian, English, and German.
  Its marketing hooks, calls to action, and mandatory phrase replacements do not apply to
  personal dictation.
- Select compact target-language guidance for Ukrainian, English, and German (plus Russian)
  in the existing Groq formatting/translation request. For same-language formatting, pass the
  selected input language as the output language for prompt guidance; automatic input detection
  uses language-neutral rules. The style rules constrain *new model wording*, not authentic
  expressions the speaker actually dictated.
- Use the original transcript as the voice sample. Formatting changes presentation and only
  a tightly bounded spelling correction; translation keeps tone and all content.
- Validate wording in order, negations, literal numbers, dates, URLs, email addresses, and
  existing question marks. Reject incomplete provider responses.
- Permit a bounded number of near-sounding corrections at matching word positions when
  unchanged neighboring words anchor the phrase. No edit may change a known negation or an
  attached negative prefix; long runs or broad rewrites still fall back to raw transcription.
- Never normalize away combining marks to force acceptance. An Arabic response that adds
  vocalization may fall back even if a reader considers it harmless.
- Keep the existing provider, models, controls, and single optional processing stage.
  Existing bounded translation retries remain. No new dependencies or model pass.
- Close each operation's provider client, including errors and validation retries.
- Freeze settings for an active recording and enforce its selected duration through the
  normal stop workflow. Stop later processing after shutdown rejects a state transition.
- Preserve disconnected and unsaved microphone selection in the settings dialog.

## Consequences

Conservative rejection can leave an unformatted transcript. Translation checks do not prove
semantic equivalence or native-speaker quality. Speech recognition may mishear the audio.
No promise is made about AI detectors or universal naturalness.
Text-only corrections cannot recover speech that was fundamentally misheard without context;
real audio comparison is needed to measure that class of error.

## Evidence

Python 3.12.14 and 3.13.7: 418 non-hardware tests passed on each; one hardware test excluded.
Ruff format, Ruff lint, and mypy passed on Python 3.13.7.
Synthetic live Groq checks: 31/32 accepted after targeted retries; Arabic formatting safely
returned the original when the model added vocalization. No real dictation or clipboard
contents were sent for these checks. Real microphone/paste acceptance remains unverified.
