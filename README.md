# WisperNext v3

WisperNext v3 is a Windows 11 accessibility-first desktop dictation application built from scratch.

Core workflow: focus a text field, start recording from a non-activating floating microphone button or an allowed global hotkey, speak, stop, transcribe with Groq, optionally punctuate or translate with Groq, then copy and optionally paste the result.

## Source of truth

Read these documents in order before writing code:

1. `docs/PROJECT_RULES.md`
2. `docs/WISPER_SPECIFICATION.md`
3. `docs/ARCHITECTURE.md`
4. `docs/AGENT_IMPLEMENTATION_GUIDE.md`
5. `docs/GIT_WORKFLOW.md`
6. `docs/IMPLEMENTATION_CHECKLIST.md`
7. `docs/IMPLEMENTATION_STATUS.md`

There is no old codebase. Build everything from scratch.

## Local repository

Expected Windows path:

```text
D:\Documents\Crypto\SOFT_CRYPTO\WisperNext_v3
```

Remote repository:

```text
https://github.com/teremno/WisperNext_v3.git
```

## Initial agent command

Use the exact prompt in `AGENT_START_PROMPT.md`.
