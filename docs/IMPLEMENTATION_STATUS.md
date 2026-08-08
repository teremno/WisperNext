# Implementation Status

## Current milestone

Milestone 3 — Safe audio vertical slice

## Status

In progress.

## Milestone 0 plan

1. Inventory the repository, Git state, packaging metadata, tests, scripts, and CI.
2. Verify editable installation and all documented quality gates on Python 3.12.
3. Correct only foundation-level defects found by those checks.
4. Record automated evidence, explicit hardware limitations, and residual risks.
5. Commit and push the completed milestone.

## Milestone 0 evidence

- Date: 2026-08-03
- Milestone commit: the `chore: verify project quality gates` commit containing this report.
- Baseline commit: `f9b7c33` (`docs: initialize WisperNext v3 project`)
- Repository state at inspection: clean `main`, synchronized with `origin/main`.
- Existing foundation: `src` package layout, Hatchling build metadata, Ruff, mypy,
  pytest, Windows CI matrix, local check scripts, and an import smoke test.
- No prior application implementation, sanitized behavior logs, packaging output, or
  hardware test evidence exists.
- Editable installation of `.[dev]` succeeded in an isolated `.venv` using bundled
  Python 3.12.13.

### Commands run

```powershell
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
.\scripts\run_checks.ps1
```

### Automated results

- `ruff format --check`: 24 files already formatted.
- `ruff check`: passed.
- `mypy src`: passed with no issues in 9 source files.
- `pytest -m "not hardware"`: 1 passed.
- Editable package import smoke test: passed.
- GitHub Actions run `30806377431`: passed on Windows with Python 3.12 and 3.13.

### Hardware results

No hardware tests were run or required for Milestone 0. No microphone-safety or
Windows focus claims are made.

## Residual risks

- Pytest passed with a local sandbox warning because the environment denied creation of
  `.pytest_cache`; test execution and results were unaffected.
- Product implementation beyond an import-safe package skeleton is intentionally absent.

## Milestone 0 next milestone

Milestone 1 — Domain and state machine.

## Milestone 1 plan

1. Define immutable typed states, user intents, operation results, and domain errors.
2. Implement one authoritative state machine with an explicit transition graph.
3. Reject illegal transitions and duplicate toggle intents without mutating state.
4. Add table-driven unit tests for every legal and illegal edge,
   toggle behavior, recovery, and shutdown.
5. Run the full quality gates, document evidence, then commit and push.

## Milestone 1 evidence

- Date: 2026-08-03
- Milestone commit: the `feat: add tested application state machine` commit containing
  this report.
- Scope: typed application states, intents, immutable snapshots/results, privacy-safe
  domain errors, authoritative transition graph, recoverable failures, retry, and shutdown.
- Concurrency: state checks and updates are serialized with `RLock`; concurrent toggles
  accept exactly one start request.
- Architecture: `docs/adr/0001-state-machine-concurrency.md` records the concurrency
  decision and keeps blocking I/O outside the state machine.

### Files changed

- `src/wispernext/domain/__init__.py`
- `src/wispernext/domain/errors.py`
- `src/wispernext/domain/models.py`
- `src/wispernext/domain/state.py`
- `tests/unit/test_state_machine.py`
- `docs/adr/0001-state-machine-concurrency.md`
- `docs/IMPLEMENTATION_STATUS.md`

### Commands run

```powershell
python -m ruff format src/wispernext/domain tests/unit/test_state_machine.py
python -m ruff check src/wispernext/domain tests/unit/test_state_machine.py
python -m mypy src
python -m pytest tests/unit/test_state_machine.py -q
.\scripts\run_checks.ps1
```

### Automated results

- `ruff format --check`: 29 files already formatted.
- `ruff check`: passed.
- `mypy src`: passed with no issues in 13 source files.
- `pytest -m "not hardware"`: 161 passed.
- Coverage includes every direct legal and illegal state edge, every active-state failure
  edge, retry, shutdown, sequential duplicate toggles, and concurrent duplicate toggles.
- GitHub Actions run `30806779680`: passed on Windows with Python 3.12 and 3.13.

### Hardware results

No hardware tests were run or required for this platform-independent milestone.

### Residual risks and unverified assumptions

- The state machine is not yet connected to an application controller or composition root.
- Transition logging and correlation lifecycle belong to later application/observability work.
- Cross-process single-instance protection is separate from in-process transition locking.

## Milestone 1 next milestone

Milestone 2 — Settings and secrets.

## Milestone 2 plan

1. Define a versioned immutable settings schema with safe defaults and strict validation.
2. Implement explicit migration from supported historical schemas and reject unknown fields.
3. Persist settings atomically, preserve corrupt files, and recover with safe defaults.
4. Define a secret-provider protocol and environment-backed Groq key adapter; never
   serialize the key into application settings. Defer key-entry UI until a writable Windows
   Credential Manager adapter is implemented and hardware-verified.
5. Add a side-effect-free composition-root skeleton and contract-focused unit tests.
6. Run all quality gates, document evidence, then commit and push.

## Milestone 2 evidence

- Date: 2026-08-03
- Milestone commit: the `feat: add validated settings and secret handling` commit
  containing this report.
- Scope: immutable versioned settings, strict type/range/enum validation, explicit
  versionless-to-v1 migration, atomic JSON persistence, corrupt-file preservation,
  per-user Windows paths, environment-backed secret lookup, and composition-root skeleton.
- Safe defaults keep auto-paste and autostart disabled and contain no credential field.
- Default Groq IDs were checked against current official Groq documentation:
  `whisper-large-v3-turbo` and `llama-3.3-70b-versatile` were available on 2026-08-03.
- Architecture: `docs/adr/0002-secure-api-key-storage.md` records the environment-only
  secret source and explicitly defers writable key UI until Credential Manager is verified.

### Files changed

- `src/wispernext/infrastructure/config.py`
- `src/wispernext/infrastructure/secrets.py`
- `src/wispernext/infrastructure/paths.py`
- `src/wispernext/bootstrap.py`
- `tests/unit/test_config.py`
- `tests/unit/test_secrets.py`
- `tests/unit/test_paths.py`
- `tests/unit/test_bootstrap.py`
- `docs/adr/0002-secure-api-key-storage.md`
- `pyproject.toml`
- `.gitignore`
- `docs/IMPLEMENTATION_STATUS.md`

### Commands run

```powershell
python -m ruff format src/wispernext/infrastructure src/wispernext/bootstrap.py tests/unit
python -m ruff check src/wispernext/infrastructure src/wispernext/bootstrap.py tests/unit
python -m mypy src
python -m pytest tests/unit/test_config.py tests/unit/test_secrets.py tests/unit/test_paths.py tests/unit/test_bootstrap.py -q
.\scripts\run_checks.ps1
rg -n --hidden -g '!.venv/**' -g '!.git/**' "api_key|WISPER_GROQ_API_KEY|gsk_" .
```

### Automated results

- `ruff format --check`: 39 files already formatted.
- `ruff check`: passed.
- `mypy src`: passed with no issues in 17 source files.
- `pytest -m "not hardware"`: 185 passed.
- Secret grep found only the documented environment-variable name, adapter/test references,
  and an explicitly fake test value; no real credential or settings field exists.

### Hardware results

No hardware tests were run or required for settings serialization or environment lookup.

### Residual risks and unverified assumptions

- The environment provider is intentionally read-only. API-key entry must not be exposed in
  the UI until a Windows Credential Manager adapter is implemented and hardware-verified.
- Groq model availability and organization permissions may change; the future Groq adapter
  must validate configuration and map unavailable/forbidden models to typed errors.
- Hotkey semantics are stored as a bounded string but will be validated in Milestone 6.
- Actual language/model behavior remains unverified until Groq milestones 4 and 7.

## Next milestone

Milestone 3 — Safe audio vertical slice. This milestone requires real Windows microphone
interaction before it can be declared complete.

## Milestone 3 plan

1. Record the Windows audio backend and stable-identity decisions in ADRs.
2. Add typed device metadata, metadata-only enumeration, deterministic identity resolution,
   and explicit ambiguity/not-found outcomes.
3. Implement one single-owner bounded capture lifecycle with idempotent cleanup, late-frame
   rejection, and fake-backend contract tests.
4. Implement raw float32 signal metrics, validation categories, and non-mutating resampling.
5. Add a concrete shared-mode Windows capture adapter without any audio-setting mutation.
6. Run all automated gates and an opt-in device enumeration smoke test.
7. Pause only for explicit real-microphone selection and the required repeated-capture test.

## Milestone 3 automated evidence (hardware gate pending)

- Date: 2026-08-03
- Scope implemented: metadata-only device catalog, non-index stable preference keys,
  ambiguity-safe resolution, connection hints, one-owner bounded capture, idempotent cleanup,
  callback status capture, raw metrics, validation categories, and linear mono resampling.
- Runtime dependency: `sounddevice` 0.5.x, isolated behind `AudioBackend` and documented in
  `docs/adr/0003-windows-audio-backend.md`.
- Stable identity limitations and no-fallback behavior are documented in
  `docs/adr/0004-stable-microphone-identity.md`.
- The local metadata-only smoke test enumerated 14 input representations across MME,
  DirectSound, WASAPI, and WDM-KS, including built-in and Bluetooth metadata. It opened zero
  streams and made no Windows audio changes.
- A Realtek WASAPI endpoint is available for an explicit first hardware test as
  `metadata:v1:a0c94924e767bb9580da02aa`.

### Automated commands and results

```powershell
python -m pip install -e ".[dev]"
.\scripts\run_checks.ps1
python -c "from wispernext.audio.backend import SoundDeviceBackend; ..."
```

- `ruff format --check`: 50 files already formatted.
- `ruff check`: passed.
- `mypy src`: passed with no issues in 21 source files.
- `pytest -m "not hardware"`: 200 passed, 1 hardware test deselected.
- The PowerShell check scripts now propagate native command failures through
  `$LASTEXITCODE`; a mypy failure can no longer be masked by a later passing pytest command.

### Hardware gate

No recording stream has been opened. Milestone 3 remains incomplete until the user explicitly
selects a microphone, authorizes a short live capture, and completes the required repeat and
independent-recorder checks. No hardware reliability claim is made.

### Hardware attempt — 2026-08-08

- User explicitly selected the Realtek WASAPI microphone with stable identity
  `metadata:v1:a0c94924e767bb9580da02aa` and authorized one 1-second capture.
- Fresh resolution found exactly one matching endpoint at runtime index `19`; the earlier
  metadata inventory had placed the same stable identity at index `12`, confirming that the
  persisted identity survives a runtime-index change.
- `sounddevice.RawInputStream` failed during construction with PortAudio error
  `Invalid device` (`PaErrorCode -9996`). No capture stream was returned, no audio frames were
  collected, and no Windows audio settings were changed.
- The service returned a recoverable `AudioSessionError`, did not try another endpoint, and
  did not automatically reopen the selected endpoint.
- A metadata-only follow-up still found the same endpoint: Windows WASAPI, 48 kHz, two input
  channels. This does not prove that the endpoint can be opened.
- Required next action: explicit user authorization for a controlled retry/format diagnostic
  on the same selected endpoint, or explicit selection of a different physical microphone.

## Agent update format

For every milestone, replace or extend this file with:

- Date and commit SHA
- Scope completed
- Files changed
- Commands run
- Automated results
- Hardware results
- Unverified assumptions
- Residual risks
- Next milestone
