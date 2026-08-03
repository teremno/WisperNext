# Project Rules

These rules override convenience and feature pressure.

1. Stability over features.
2. Simplicity over cleverness.
3. Build from scratch; no legacy assumptions.
4. Windows 11 is the primary supported platform.
5. Never mutate Windows audio or input configuration.
6. One recording lifecycle owns at most one capture stream.
7. The user explicitly controls microphone selection.
8. No silent microphone fallback.
9. The floating button must not steal keyboard focus.
10. Global hotkeys must work with Windows On-Screen Keyboard input where Windows exposes it normally.
11. Unmodified letters, digits, and ordinary punctuation are forbidden global hotkeys.
12. Groq is the only cloud provider in the first stable version.
13. No OpenAI, OpenRouter, local Whisper, spelling engine, grammar engine, vocabulary engine, or rewrite subsystem in v1.
14. Groq text processing may add punctuation, capitalization, paragraph breaks, or translate. It must not invent facts or freely rewrite text.
15. No blocking work on the UI thread.
16. No secrets or dictated text in logs.
17. Every failure must leave the app recoverable or safely shut down.
18. Do not add a dependency without documenting why it is needed.
19. Prefer a smaller tested component over a large abstraction hierarchy.
20. Do not claim hardware reliability based only on mocks.
