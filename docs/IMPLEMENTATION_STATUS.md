# Implementation Status

## Current milestone

Milestone 7 — Groq formatting and multilingual output

## Status

Complete.

## Milestone 7 plan

1. Add a bounded Groq text-processing adapter using a current multilingual model and structured
   output, with the API key resolved only through the existing secret provider.
2. Implement conservative formatting/translation policy, prompt isolation, fixed output caps,
   typed provider failures, and final fallback validation that preserves the raw transcript.
3. Expose Auto plus all 15 supported input languages, Same-as-input plus all 15 output languages,
   and safe formatting in the settings UI.
4. Integrate `FORMATTING_OR_TRANSLATING` into the controller without blocking the Qt thread.
5. Fix and regression-test the real Windows auto-paste ABI failure found during Milestone 7 intake.
6. Run unit, integration, real Windows delivery, and opt-in Groq checks; document evidence and risks.
7. Commit, push, and verify CI.

## Milestone 7 completion

- Date: 2026-08-08
- Scope: separate Auto/fixed input language and Same-as-input/fixed output language controls;
  all 15 specified languages; conservative punctuation/paragraph formatting; cross-language
  translation; schema-bound Groq output; final safety validation; raw-transcript fallback; and
  controller integration through `FORMATTING_OR_TRANSLATING`.
- Current-provider validation: Groq documents `whisper-large-v3-turbo` as multilingual with 99+
  languages and recommends it for multilingual price/performance. Groq also documents
  `openai/gpt-oss-120b` as multilingual across 81+ languages. The previous default
  `llama-3.3-70b-versatile` is scheduled for shutdown on 2026-08-16, so settings schema v4 migrates
  only that previous default to `openai/gpt-oss-120b`.
- Official evidence:
  - https://console.groq.com/docs/speech-to-text
  - https://console.groq.com/docs/model/whisper-large-v3-turbo
  - https://console.groq.com/docs/model/openai/gpt-oss-120b
  - https://console.groq.com/docs/deprecations
- Safety: transcript content is JSON-escaped and treated as untrusted data; the provider receives
  no tools; structured output is strict; temperature is 0.1; reasoning effort is low; output is
  capped at 2,048 tokens; timeout is bounded; retry count is one; and no credential or dictated
  text is logged. Empty, wrapped, meta-commentary, wrong-language, changed-number, excessive-length,
  and excessive same-language rewrite results fall back to the raw transcript with a visible notice.
- UI: the settings dialog now exposes all 15 languages independently for input and output, plus
  safe formatting. Offscreen layout QA confirmed the expanded dialog remains readable without
  clipped groups or controls.

### Verification evidence

```powershell
python -m ruff format --check .
python -m ruff check .
python -m mypy src
python -m pytest -m "not hardware"
python scripts/run_live_text_processing_smoke.py
python scripts/run_auto_paste_smoke.py
```

- Ruff and strict mypy passed.
- `pytest -m "not hardware"`: 314 passed, 1 hardware test deselected.
- One live formatting request and live translation into every one of the 15 advertised output
  languages passed through the configured Groq credential with no fallback or validation failure.
- Ukrainian-to-English and English-to-Ukrainian were included explicitly in the live matrix.
- No microphone was opened by the text-processing or auto-paste smoke tests.

### Auto-paste defect fixed during intake

- The user's persisted setting was confirmed as `auto_paste = true`; clipboard delivery was already
  successful, so the failure was in the Win32 input adapter rather than configuration.
- The real disposable-field smoke test reproduced `INPUT_REJECTED`.
- Root cause: the local `INPUT` union omitted `MOUSEINPUT`, making `ctypes.sizeof(INPUT)` 32 bytes on
  64-bit Windows instead of the required 40-byte Win32 ABI. `SendInput` therefore rejected all four
  key events.
- The adapter now defines the complete union and a regression test asserts 40 bytes on x64 (28 on
  x86). The repeated real test returned `PASTED`, and the disposable field received the exact
  sentinel while the user's previous clipboard text was restored.
- Auto-paste refusal statuses now surface a privacy-safe visible notice instead of failing silently.
- The old desktop process was replaced after exact executable-path validation. The updated desktop
  composition started and closed cleanly, the real paste smoke passed again, and the updated app was
  then launched through the existing desktop shortcut and left running.

### Residual risks

- Windows integrity isolation can still reject paste into an elevated target from a non-elevated
  WisperNext process; the text remains verified in the clipboard and the UI reports the refusal.
- Provider language is validated from schema-bound output plus requested-code matching. The live
  15-language matrix passed, but model behavior can change and remains covered by the fallback.
- A dispatched Groq SDK request is timeout-bounded but cannot be cancelled after dispatch in the
  current synchronous SDK integration.

## User-requested launch and settings bridge

- Date: 2026-08-08
- Reason: the user has no physical keyboard and needs a discoverable mouse-only launch and
  configuration path before the later packaging milestone.
- Added a real `Налаштування…` tray action, tray-icon double-click, and right-click access from the
  floating button. The settings window exposes system-default/manual microphone selection, device
  refresh, auto-paste, maximum recording duration, and floating-button launch preference.
- Microphone enumeration and settings persistence run on the existing serialized worker. Refreshing
  the list enumerates metadata only and never opens an audio stream or changes Windows audio settings.
- Added `scripts/create_development_shortcut.ps1` and used it to create
  `C:\Users\Oleksandr\Desktop\WisperNext.lnk` for the current local editable build.
- Read-back validation confirmed the shortcut target and arguments. Launching it twice left exactly
  one WisperNext process, confirming the shortcut follows the existing single-instance guard.
- This is not the Milestone 9 installer: automatic shortcut creation during install, Start menu,
  upgrade, and uninstall behavior remain pending and the packaging checklist stays open.
- Automated evidence: 295 tests passed with one hardware test deselected; Ruff and strict mypy
  passed. Offscreen visual QA found and corrected a low-contrast form-label style.

## Milestone 6 plan

1. Add a Win32 named-mutex single-instance guard with deterministic cleanup.
2. Add strict hotkey parsing/validation and a `RegisterHotKey` adapter with no keyboard hook.
3. Add a non-activating, always-on-top, draggable PySide6 floating control with accessible
   metadata and shape-plus-color state rendering.
4. Migrate settings schema v2 to v3 for logical button coordinates and keep them on a visible
   screen after display changes.
5. Add a background dictation controller connecting state, audio, Groq, clipboard, and optional
   safe paste without blocking the Qt thread.
6. Replace the placeholder entry point and add deterministic contract/UI tests.
7. Verify real focus behavior, single instance, physical hotkey, and Windows On-Screen Keyboard;
   document only the scenarios actually observed.
8. Commit, push, and verify CI.

## Milestone 6 automated implementation and Windows evidence

- Date: 2026-08-08
- Status: implementation complete; keyboard compatibility gate pending external hardware.
- Scope: PySide6 floating control, industrial high-contrast state rendering, accessibility
  metadata, non-activating Win32 style, dragging and multi-monitor position recovery, settings
  schema v3, strict hotkey parser, `RegisterHotKey` adapter, Qt native event bridge, named-mutex
  single instance, minimal tray Exit action, and serialized background dictation controller.
- Architecture: `docs/adr/0007-non-activating-floating-button.md` and
  `docs/adr/0008-global-hotkey-and-single-instance.md` record the dependency, focus, accessibility,
  hotkey, OSK, and process-ownership decisions.
- Dependency: `PySide6-Essentials` 6.11.1 installed locally. Addons were intentionally omitted.

### Automated commands and results

```powershell
python -m pip install -e ".[dev]"
python -m ruff format --check .
python -m ruff check .
python -m mypy src
python -m pytest -m "not hardware"
python scripts/render_button_states.py
python scripts/run_desktop_smoke.py
python scripts/run_focus_button_smoke.py
python scripts/run_hotkey_smoke.py F8 --self-send-f8
```

- `ruff format --check`: passed.
- `ruff check`: passed.
- `mypy src`: passed with no issues in 36 source files.
- `pytest -m "not hardware"`: 289 passed, 1 audio hardware test deselected.
- The full desktop composition displayed the real floating control and tray, registered resources,
  entered ready state, then closed cleanly with exit code 0 without opening a microphone.
- Visual QA rendered all six required states. Each uses a distinct geometric symbol as well as a
  distinct color; no animation or extra status panel was added.

### Windows focus and hotkey evidence

- The first focus harness used Qt logical coordinates and missed the button under display scaling;
  no callback ran and no focus conclusion was drawn.
- The corrected harness used the native HWND rectangle. A real OS-level mouse click invoked the
  button while preserving both the foreground target window and the text-field focus.
- `RegisterHotKey(F8)` plus a Windows input self-send produced `WM_HOTKEY`. Qt 6.11.1 delivered the
  event as `windows_generic_MSG`, so the adapter now accepts both Qt-documented dispatcher and
  observed generic Windows message types while still matching the exact Wisper message ID.
- Two manual physical-F8 listener windows expired without receiving a user key press. The user
  later confirmed that only an on-screen keyboard is available, so a physical-keyboard test cannot
  be completed in this environment and no physical failure is inferred.
- Windows On-Screen Keyboard opened successfully, but its protected accessibility tree exposed no
  individual key controls to UI Automation. The initial 60-second F8 listener expired without an
  observed hotkey event, and OSK was then closed normally.
- `Ctrl+Alt+M` was unavailable because Windows or another process already owned it. Registration-only
  probes verified that `Ctrl+Shift+M`, `Ctrl+Alt+W`, `Ctrl+Shift+W`, `Ctrl+Alt+G`, and `Ctrl+M` were
  available without opening the microphone.
- Guided 120-second `Ctrl+Shift+M` and 90-second `Ctrl+M` OSK listener sessions both expired without
  a `WM_HOTKEY` event. This is documented as an environment/OSK compatibility result, not as proof
  that the user pressed or did not press a key sequence.
- The verified keyboard-free path is the non-activating floating button, operated with the mouse.
  It uses the same start/stop action as the hotkey and has already passed the real focus-preservation
  test. The OSK documentation checklist item is complete; physical hotkey compatibility and a
  successful OSK hotkey remain open, so Milestone 6 is not declared complete yet.

### Residual risks

- Exact focus preservation is verified with a disposable native test field, not yet with Notepad,
  browser, and a third desktop application.
- Protected/elevated target windows may reject input, and some system hotkeys may already be owned.
- Windows On-Screen Keyboard did not produce an observed global-hotkey event in the guided tests;
  users without a physical keyboard must use the verified floating button until this is resolved.
- The controller's Groq request is timeout-bounded but cannot be cancelled after SDK dispatch.
- The settings UI for changing the default F8 hotkey belongs to Milestone 8.

## Milestone 5 plan

1. Add a typed clipboard port and verified delivery service with bounded retries.
2. Preserve and restore the previous Unicode text when delivery fails after mutation.
3. Add pure conservative auto-paste policy based on setting, verified clipboard, application
   state, exact foreground context, and non-Wisper ownership.
4. Add a bounded Windows adapter that sends one `Ctrl+V` only after rechecking the expected
   foreground window; never force focus or retry input.
5. Cover behavior with deterministic fakes in normal CI.
6. Run an opt-in Windows clipboard smoke test that restores the original clipboard text.
7. Document evidence and residual risks, then commit, push, and verify CI.

## Milestone 5 completion

- Date: 2026-08-08
- Scope: typed verified clipboard delivery, exact read-back, three-attempt bounded retry policy,
  previous Unicode-text restoration, conservative auto-paste decision logic, foreground context,
  and Win32 clipboard/`SendInput` adapters.
- Architecture: `docs/adr/0006-focus-context-and-auto-paste.md` records the exact-context and
  one-attempt policy. Wisper never calls `SetForegroundWindow`, simulates clicks, searches for
  another target, or retries paste input.
- Composition remains side-effect-free: Win32 adapters are constructed at bootstrap but do not
  access the clipboard or foreground window until explicitly invoked.

### Automated commands and results

```powershell
python -m ruff format --check .
python -m ruff check .
python -m mypy src
python -m pytest -m "not hardware"
python scripts/run_clipboard_smoke.py
```

- `ruff format --check`: passed.
- `ruff check`: passed.
- `mypy src`: passed with no issues in 28 source files.
- `pytest -m "not hardware"`: 246 passed, 1 hardware test deselected.
- Contract tests prove exact verification, bounded retry, successful restoration, explicit restore
  failure, zero writes when initially unavailable, all policy denials, and exactly one safe paste
  attempt.

### Windows evidence

- The opt-in Unicode clipboard smoke test succeeded on the first delivery attempt.
- The test read the original text only in memory, wrote a random sentinel, verified exact equality,
  restored the original text, and verified the restoration. No clipboard content was printed or
  persisted.
- Real `Ctrl+V` was intentionally not sent because no disposable target field was explicitly
  prepared. This avoids modifying whichever user application happened to have focus.

### Residual risks and unverified assumptions

- Windows clipboard content that has no Unicode-text representation cannot be restored by this
  text-only adapter after a rare failure occurring after `EmptyClipboard`; that outcome is reported
  as `RESTORE_FAILED`. The verified happy path replaces clipboard content as normal copy behavior.
- Some elevated or protected applications may reject `SendInput`; Wisper reports `INPUT_REJECTED`
  and leaves verified text in the clipboard.
- Exact foreground window/process/thread matching cannot prove the caret stayed in the same control.
  This intentionally causes conservative clipboard-only fallback and requires real application tests
  during the floating-button/reliability milestones.

## Milestone 5 next milestone

Milestone 6 — single-instance application, non-activating floating button, toggle behavior, visible
states, allowed global hotkeys, and Windows On-Screen Keyboard verification.

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

Real capture and the required 100-cycle test pass on the explicitly selected Realtek WASAPI
endpoint. The user then verified that Windows Sound Recorder could record and play back speech
after the test. No broader USB/Bluetooth hardware reliability claim is made.

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
- This failure was produced by sandboxed device access, not by an unsupported mono/stereo
  format. It remains valid recoverable-error evidence.

### Successful hardware retry — 2026-08-08

- `sounddevice.check_input_settings` confirmed that the selected Realtek WASAPI endpoint
  supports mono and stereo float32 capture at 48 kHz.
- An explicitly approved unsandboxed 2-second capture succeeded on the same stable identity
  at runtime index `19`: 96,000 frames, RMS `0.00018477`, peak `0.00605236`, clipping ratio
  `0.0`, and no callback status flags.
- Validation returned `WEAK_SIGNAL` because almost no speech was present; this is a signal
  result, not a stream failure. Audio was not saved.
- The opt-in hardware test completed 100 sequential open/capture/stop/close cycles on the
  same endpoint: `1 passed` in 51.91 seconds. Each capture produced frames; no fallback device
  was opened.
- No Python, WisperNext, or PortAudio test process remained after completion.
- The only test warning concerned denied creation of `.pytest_cache`; it did not affect audio
  capture or the test result.
- The user confirmed that Windows Sound Recorder successfully recorded and played back speech
  after the 100-cycle test.

### Milestone 3 completion

- Date: 2026-08-08
- Milestone commit: the `test: verify safe Windows audio lifecycle` commit containing this
  final evidence.
- Exit condition satisfied for the selected built-in Realtek microphone: 100 sequential
  recordings completed without preventing subsequent recording in an independent application.
- Automated fake-backend contracts and the real hardware result support the single-owner,
  exact-device, bounded-capture, idempotent-cleanup behavior.
- Residual hardware scope: USB and Bluetooth capture, disconnect/reconnect, suspend/resume,
  and other required matrix scenarios remain explicitly unverified until later reliability
  milestones. They are not claimed as working.

## Milestone 3 next milestone

Milestone 4 — Groq transcription. A real API smoke test will require explicit use of the
user-controlled Groq credential; normal CI will use fakes and make no live cloud calls.

## Milestone 4 plan

1. Add an explicit microphone-selection mode: `system_default` by default or a manually
   persisted stable device identity, with no physical-device fallback.
2. Migrate settings schema v1 to v2 atomically and test both selection paths.
3. Add the official Groq Python SDK behind a typed transcription port.
4. Encode validated mono float32 audio to an in-memory 16 kHz PCM WAV; never upload weak,
   empty, clipped, or too-short captures.
5. Configure bounded connect/read/write/total timeouts and one SDK-managed retry for transient
   connection, timeout, 408, 409, 429, and server failures only.
6. Map provider failures to privacy-safe typed results without logging audio, keys, or text.
7. Cover behavior with fakes/mocked SDK responses; normal CI must make zero Groq calls.
8. Run a single user-authorized live transcription smoke test with the process-scoped key,
   record only metrics/status (not dictated text), then complete, commit, and push.

## Milestone 4 initial evidence

- Date: 2026-08-08
- `WISPER_GROQ_API_KEY` is configured in the current process environment and has the expected
  `gsk_` shape. Its value was not displayed, logged, copied, or written to settings.
- No Groq credential exists in User/Machine environment scope or in a Credential Manager
  target containing `groq`. A normally launched installed app may therefore need persistent
  secure-key setup later; the current development process can use the existing key.
- Official Groq documentation currently lists `whisper-large-v3-turbo` as multilingual STT,
  recommends 16 kHz mono preprocessing, and supports direct WAV uploads.

## Milestone 4 completion

- Date: 2026-08-08
- Scope: system-default/manual microphone selection policy, settings schema v2 migration,
  read-only microphone catalog, validated in-memory PCM16 WAV preparation, official Groq SDK
  adapter, bounded timeouts and retry, privacy-safe typed failures, and lazy composition.
- Architecture: `docs/adr/0005-groq-transcription-provider.md` records the Groq-only provider,
  model, privacy, retry, timeout, and verification decisions.
- The default-device smoke resolved Windows default to `Depstech webcam MIC`. Its 5.899-second
  capture was correctly categorized `WEAK_SIGNAL` (`RMS 0.00050819`, peak `0.00854492`) and
  caused zero Groq uploads.
- The user had explicitly selected the Realtek WASAPI endpoint for the manual path. Its
  6.0-second capture was `VALID_AUDIO` (`RMS 0.06466251`, peak `0.41552398`, clipping `0.0`).
  One live Groq request succeeded and returned 71 transcript characters. Neither transcript
  content nor API-key content was printed, logged, or persisted.

### Automated commands and results

```powershell
python -m ruff format --check .
python -m ruff check .
python -m mypy src
python -m pytest -m "not hardware"
python scripts/run_live_transcription_smoke.py --seconds 6
python scripts/run_live_transcription_smoke.py --seconds 6 --microphone-id <stable-id>
```

- `ruff format --check`: passed.
- `ruff check`: passed.
- `mypy src`: passed with no issues in 25 source files.
- `pytest -m "not hardware"`: 229 passed, 1 hardware test deselected.
- Unit tests use fakes/mocked SDK objects and make zero cloud requests.

### Residual risks and unverified assumptions

- The settings UI does not yet expose key replacement/deletion, although the tested credential
  service supports both operations.
- The synchronous Groq SDK call cannot be cancelled after dispatch; strict total/read/write/
  connect timeouts bound it instead. Controller-level background execution belongs to the UI
  integration milestone.
- The current Windows default microphone is too quiet for reliable transcription. Wisper does
  not change it; manual Realtek selection works and remains the safe choice for now.
- Provider availability, rate limits, and model permissions remain external runtime conditions.

### Windows Credential Manager follow-up — 2026-08-08

- Added a native, dependency-free Generic Credential adapter using `CredReadW`, `CredWriteW`,
  `CredDeleteW`, and `CredFree`.
- Persisted the existing process key under the user-scoped target `WisperNext/GroqApiKey` and
  verified an exact in-memory round trip without printing or writing the value elsewhere.
- Removed `WISPER_GROQ_API_KEY` from a child-process environment and successfully authenticated
  to Groq using only Credential Manager; the account returned 15 visible models.
- Wisper now prefers Credential Manager and uses the environment variable only as a development
  fallback. Explicitly injected test environments remain isolated from the real Windows store.

## Milestone 4 next milestone

Milestone 5 — Clipboard delivery with verification and conservative optional auto-paste.

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
