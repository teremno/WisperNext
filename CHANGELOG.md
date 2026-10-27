# Changelog

## 2026-10-27: application icon

- Before: the desktop shortcut showed the Python icon.
- Now: `assets/wispernext.ico` holds a microphone icon in 10 sizes (16–256 px), matching the
  tray icon. `scripts/create_development_shortcut.ps1` uses it; `scripts/render_app_icon.py`
  regenerates it.

## 2026-10-27: Ukrainian dictation accuracy ([#3](https://github.com/teremno/WisperNext/pull/3))

### Starting point

- Ukrainian dictation, especially from a distant microphone, produced nonsense words and a
  comma at every pause.
- Local diagnostics from 21 Aug to 27 Oct: 1,270 of about 6,900 dictations (18 %) fell back
  to the raw Whisper transcript (781 `invalid_request`, 489 `unsafe_response`).
- Causes found in the code:
  - Default model `whisper-large-v3-turbo`: 12 % WER by Groq's own figures, against 10.3 %
    for `whisper-large-v3`.
  - Whisper received no prompt, so nothing steered its vocabulary or punctuation.
  - The wording validator required the same word count and words of 4+ letters. It rejected
    7 of 9 typical Ukrainian repairs: split or merged words, `в` → `у`, `та` → `то`.
  - The resampler had no low-pass filter: 87 % of a 10 kHz tone landed in the speech band.
  - The formatter prompt asked to add punctuation and never to remove pause commas.
  - The desktop shortcut ran a second, unpublished copy of the project.

### Changes

- Default model `whisper-large-v3`; settings schema 6 moves the old Turbo default to it.
- Whisper gets a short Ukrainian prompt with grammatical punctuation.
- `verbose_json`: segments Whisper scores as silence, echoes of the prompt, and trailing
  subtitle lines ("Дякую за перегляд!") after real speech are dropped.
- Audio up to 24 MB is sent at its native rate and Groq resamples it. The local fallback
  resampler got a low-pass filter (10 kHz tone residue 0.307 → 0.079 RMS).
- The validator accepts re-spaced words, one-sound fixes of short words, and dropped
  hesitation sounds. Negations, pronouns, insertions, and other deletions still fall back to
  the raw transcript.
- The formatter punctuates by grammar, not pauses, and removes commas grammar does not need.
- A Groq `json_validate_failed` answer is logged as `invalid_output` and retried once.
- One project copy remains: the shortcut runs this repository; the old copy was removed.

### Verified

- Ruff, mypy strict, and 479 tests on Python 3.12 and 3.13; GitHub CI passed.
- Live Groq run on synthetic Ukrainian text repaired merged words, pause commas, and
  hesitation sounds.

### Not solved

- On pure noise Whisper can still return "Дякую за перегляд!"; the filter keeps it when it is
  the whole dictation.
- No recordings of the owner's voice were tested, so the gain in word accuracy is unmeasured.
- Builds older than schema 6 cannot read settings written by this build.
