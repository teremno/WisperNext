# Wisper — Complete Product and Engineering Specification for an Autonomous Coding Agent

## 1. Purpose of this document

This document is the authoritative implementation specification for rebuilding Wisper as a stable Windows 11 desktop dictation application.

The coding agent must use this document as the primary source of truth. This project is built from scratch. There is no legacy codebase. The agent must not search for, infer, copy, or recreate any previous implementation.

The main priority is not feature count. The main priority is:

> Press once, speak, press again, receive the correct text, and keep the application and Windows stable.

The agent must proceed phase by phase without asking for routine implementation decisions. It may stop only when:

- an operating-system permission or external account authorization is required;
- a Groq API key or other user-controlled secret is required;
- a real hardware action is required from the user;
- a destructive, privacy-expanding, or system-mutating action would be necessary;
- two requirements in this document are genuinely impossible to satisfy together;
- continuing would risk changing Windows audio settings or damaging user data.

In all other cases, the agent must make the safest reasonable engineering choice, document it, implement it, test it, and continue.

---

## 2. Product mission

Wisper is an accessibility-first desktop dictation application for Windows 11. It is intended for people who cannot comfortably or reliably type on a physical keyboard and may use the Windows On-Screen Keyboard or other accessibility input methods.

The core workflow is:

1. The user places the text cursor in an editable field in another application.
2. The user starts recording by clicking Wisper's floating microphone button or by using a configured global hotkey.
3. Wisper records from the explicitly selected microphone.
4. The user stops recording by clicking the same button or pressing the same hotkey again.
5. Wisper validates the recording.
6. Wisper sends valid audio to Groq for transcription.
7. Wisper optionally sends the transcript to a Groq language model for punctuation, capitalization, paragraph breaks, or translation.
8. Wisper copies the final result to the clipboard.
9. If reliable auto-paste is enabled and the target remains safe, Wisper pastes into the intended field.
10. Wisper returns to the ready state.

The application must favor predictability, accessibility, recoverability, and low complexity over aggressive automation.

---

## 3. Product priorities

Priority order:

1. Windows and microphone safety.
2. Stable repeated recording.
3. Preserving the user's text cursor and active application.
4. Accurate transcription.
5. Reliable clipboard delivery.
6. Translation and punctuation.
7. Convenience features.

No lower-priority feature may weaken a higher-priority requirement.

---

## 4. Non-negotiable Windows and microphone safety

Wisper must behave as a contained microphone client. It must never attempt to repair, reconfigure, reset, disable, restart, or otherwise mutate Windows audio configuration.

Wisper must never:

- change the Windows default input device;
- change the Windows default output device;
- change microphone volume or microphone boost;
- change exclusive-mode settings;
- change Windows microphone privacy settings;
- modify audio drivers;
- disable or enable audio devices;
- restart Windows Audio services;
- modify the registry to repair audio;
- install drivers or codecs as a repair strategy;
- cycle through physical microphones by opening recording streams;
- silently switch to a different physical microphone;
- repeatedly reopen a failing microphone in a tight loop;
- call global PortAudio terminate/reinitialize functions during normal runtime;
- use background microphone probing.

Wisper may only:

- enumerate microphone metadata;
- remember the user's selected microphone;
- resolve that selection to the current runtime device;
- open exactly one selected input endpoint when recording starts;
- capture audio;
- stop and close the stream deterministically;
- report actionable errors.

If a selected device disappears or becomes unavailable, Wisper must enter a recoverable error state and wait for an explicit retry or new selection. It must not select another physical microphone automatically.

Bluetooth microphones and Bluetooth headset microphones must be supported. They are subject to the same no-auto-switch and single-stream rules as other devices.

---

## 5. Required user experience

### 5.1 Installation and launch

The Windows installer must:

- install Wisper in an appropriate per-user or machine location;
- create a Start menu entry;
- create a desktop shortcut automatically;
- install all required runtime components that can legally and safely be bundled;
- preserve user settings during ordinary upgrades;
- support clean uninstall;
- never delete user data without explicit user action.

Autostart with Windows is optional and disabled by default unless the user explicitly enables it.

The application must be single-instance. Launching the desktop shortcut while Wisper is already running must not start a second process with a second microphone owner.

### 5.2 Floating microphone button

When Wisper starts, it must show a floating microphone button.

The button must:

- remain above ordinary windows;
- be draggable;
- remember its last screen position;
- remain visible after restart;
- support display scaling and multiple monitors;
- never become the owner of application state;
- send only user intents to the application controller;
- not steal keyboard focus from the current text field when clicked;
- not activate Wisper as the foreground application merely because it was clicked;
- remain usable with mouse, touch, and accessibility tools where Windows permits it.

The preferred Windows implementation is a non-activating tool window. The coding agent must verify the exact focus behavior on real Windows 11 hardware. A visually correct button that steals focus is not acceptable.

### 5.3 Button interaction

The button uses toggle behavior:

- first click: start recording;
- second click: stop recording;
- clicks during opening, stopping, or processing are ignored or safely rejected;
- duplicate clicks must never create parallel audio or network operations.

The button must clearly represent these states without relying on color alone:

- READY;
- OPENING;
- RECORDING;
- PROCESSING;
- ERROR;
- DISABLED or SHUTTING_DOWN.

The icon or visible shape must change in addition to color. The exact colors are an implementation detail, but recording and processing must be clearly distinguishable.

Do not add decorative status bubbles, unnecessary animations, or separate text-action panels in the first stable version.

### 5.4 Cursor and focus behavior

This is a critical accessibility requirement.

When the user places the text cursor in another application and clicks the floating button:

- the target application should remain active;
- the text cursor should remain in the same field;
- Wisper must not deliberately activate its own settings window or floating button window;
- recording must start without requiring the user to restore focus manually.

Wisper must record enough target context to make delivery safer, such as the foreground window identity and process at recording start. It must not capture private text from the target application.

If the target context clearly changed before delivery, auto-paste must not blindly insert text into an unrelated application. In that case, Wisper must keep the result in the clipboard and expose a small, non-blocking error or status indication.

The application must not use aggressive focus stealing, forced window activation, repeated simulated clicks, or arbitrary UI automation to recover focus.

---

## 6. Global hotkeys and On-Screen Keyboard compatibility

### 6.1 General rule

Wisper must support global hotkeys, including input generated by the Windows On-Screen Keyboard where Windows delivers it through normal keyboard input paths.

The hotkey implementation must not assume a physical keyboard.

### 6.2 Allowed hotkeys

The settings UI may allow:

- function keys F1–F24 where supported;
- Pause/Break;
- Insert;
- Home;
- End;
- Page Up;
- Page Down;
- Scroll Lock;
- supported numpad special keys;
- supported media or special keys;
- modifier combinations using Ctrl, Alt, Shift, or Win plus a permitted key.

### 6.3 Forbidden single-key hotkeys

The following are forbidden as unmodified global hotkeys:

- letters A–Z;
- top-row digits 0–9;
- ordinary punctuation and typing symbols, including slash, backslash, period, comma, semicolon, apostrophe, brackets, minus, equals, and similar keys.

This prevents normal typing from unexpectedly starting or stopping recording.

Letters, digits, or symbols may be used only as part of a safe modifier combination when Windows can register the combination reliably.

### 6.4 Hotkey behavior

The same configured hotkey toggles recording:

- first activation starts recording;
- second activation stops recording;
- activation during OPENING, STOPPING, or PROCESSING must not create duplicate work.

The application must test hotkey reception from:

- a physical keyboard;
- the Windows On-Screen Keyboard;
- at least one permitted single special key;
- at least one modifier combination.

A hotkey is not considered supported until it is verified on Windows 11.

---

## 7. Microphone selection and diagnostics

### 7.1 Manual selection

The user must be able to select a microphone explicitly in settings.

The device list should show useful metadata where available:

- friendly name;
- connection or backend type, such as USB, Bluetooth, internal, webcam, or virtual;
- host API/backend;
- native/default sample rate;
- maximum input channel count;
- whether the device is currently available;
- stable Windows endpoint identity where available.

Do not use a raw PortAudio index as the persistent device identity.

Store a stable preference using the best available Windows endpoint identifier plus last-seen metadata. Resolve it to the current runtime index during enumeration.

When resolution is ambiguous, ask the user to select a device. Do not guess.

### 7.2 First-run recommendation

On first run, Wisper may suggest a microphone based only on metadata. The user must confirm it.

After confirmation, Wisper must not automatically switch to another physical microphone.

If the user selected “System default,” Wisper may resolve the current system default at recording time because that is the explicit user preference. It still must not change the Windows default.

### 7.3 Refresh

Refreshing the device list must enumerate metadata only. It must open zero audio streams.

### 7.4 Test microphone

Settings must include an explicit “Test microphone” action.

The test must:

- start only after user action;
- use the selected microphone;
- record a short bounded sample;
- show a simple input level indication;
- display duration, RMS, peak, clipping ratio, and frame count;
- allow playback only if it can be implemented safely and simply;
- close the stream deterministically;
- not change Windows settings;
- not continue in the background.

### 7.5 Diagnostics and support report

A Diagnostics section must exist under Settings.

It must include:

- selected stable device identity;
- currently resolved runtime device;
- backend/host API;
- native sample rate and channels;
- last capture duration;
- raw RMS and peak;
- clipping ratio;
- frame count;
- callback status or overflow flags;
- last structured error;
- application version;
- Windows version;
- Python/runtime version if applicable;
- configured provider and model identifiers;
- a privacy-safe correlation ID.

It must include a user-facing action named similar to “Create support report.”

The report must never contain:

- the Groq API key;
- complete dictated text;
- clipboard contents;
- audio recordings;
- personal file paths unless required and clearly redacted;
- unrelated application content.

---

## 8. Groq-only provider policy for the first stable version

The first stable version uses Groq for all remote AI operations.

Required remote components:

1. Groq speech-to-text provider.
2. Groq language-model provider for punctuation/formatting and optional translation.

Do not implement OpenAI, OpenRouter, or additional translation APIs in the first stable version.

Provider abstractions must still be clean enough to permit replacement later without rewriting the domain or user interface.

### 8.1 Secret handling

The Groq API key must never be stored in plain-text application settings or logs.

Preferred options:

- Windows Credential Manager; or
- a user environment variable such as `WISPER_GROQ_API_KEY`.

If the settings UI allows entering the key, it must immediately store it through the selected secure secret adapter and never write it into `settings.json`.

The UI may show only whether a key is configured. It must not display the full key after saving.

### 8.2 Network behavior

All Groq calls require:

- connection timeout;
- total timeout;
- bounded retry only for clearly transient failures;
- no retry loops;
- cancellation where practical;
- structured error mapping;
- no secret or full dictated text in logs.

Weak, empty, or too-short audio must not be sent to Groq.

If Groq is unavailable, Wisper must fail safely, keep the audio only as long as required by the configured privacy policy, return to a usable state, and provide an actionable error. The first stable version does not require a local transcription fallback.

---

## 9. Language behavior

Wisper must support multilingual dictation and output.

### 9.1 Separate input and output language

The settings UI must separate:

- Input language;
- Output language.

Input language options:

- Auto-detect;
- a supported fixed language.

Output language options:

- Same as input;
- a supported fixed language.

Examples:

- Ukrainian speech → Ukrainian text;
- Ukrainian speech → English text;
- English speech → Ukrainian text;
- French speech → German text.

### 9.2 Initial supported languages

The first stable version must support at least these 15 language choices when supported by the selected Groq models:

- English;
- Ukrainian;
- German;
- French;
- Spanish;
- Italian;
- Portuguese;
- Polish;
- Dutch;
- Turkish;
- Arabic;
- Hindi;
- Chinese, Simplified;
- Japanese;
- Korean.

The agent must validate actual model support against current Groq documentation during implementation. Unsupported language/model combinations must not be falsely advertised.

### 9.3 Processing rules

When Output language is “Same as input”:

- preserve the detected or fixed input language;
- apply only safe formatting if enabled.

When Output language is fixed and differs from the input:

- translate the transcript to the selected output language;
- preserve meaning;
- do not add explanations;
- do not answer questions contained in the dictated text;
- do not summarize;
- return only the translated text.

---

## 10. Text processing — deliberately simple

The first stable version must avoid a large text-processing pipeline.

Do not implement separate modules for:

- spell checking;
- grammar checking;
- style rewriting;
- vocabulary profiles;
- custom word replacement;
- semantic rewriting;
- duplicate-history management;
- text-action buttons;
- arbitrary voice commands;
- Markdown generation;
- document summarization.

The processing path should remain:

```text
captured audio
  -> audio validation
  -> Groq transcription
  -> optional Groq formatting or translation
  -> final safety validation
  -> clipboard
  -> optional paste
```

### 10.1 Formatting mode

Formatting may:

- add punctuation;
- correct capitalization;
- add paragraph breaks;
- normalize obvious spacing;
- preserve the requested output language.

Formatting must not:

- add new facts;
- answer the user's dictated question;
- summarize;
- remove meaningful content;
- replace wording unnecessarily;
- change names or numbers without strong evidence;
- produce Markdown unless explicitly required by a future feature;
- add commentary such as “Here is the corrected text.”

The default prompt must instruct the model to return only the final text.

### 10.2 Avoiding an overly rigid formatter

The formatter must not be so restrictive that obvious transcription mistakes remain untouched when they prevent readable output. However, changes beyond punctuation, capitalization, spacing, and clearly necessary correction must be conservative.

Any broader rewrite feature is out of scope for the first stable version.

### 10.3 Final validation

Before delivery, Wisper must reject or fall back to the raw transcript if the LLM result:

- is empty while the transcript was not empty;
- adds meta-commentary;
- is unexpectedly much longer or much shorter;
- changes the requested language;
- appears to answer or discuss the text instead of formatting or translating it;
- contains obvious formatting wrappers not requested by the user.

If formatting or translation fails, Wisper must preserve the original transcription and may deliver it when safe, clearly indicating that the optional transformation failed.

---

## 11. Clipboard and auto-paste

### 11.1 Clipboard is mandatory

After successful processing, Wisper must copy the final text to the clipboard.

It must:

- write the text;
- read it back;
- verify equality within a bounded retry window;
- return a structured result;
- not erase the user's clipboard if delivery fails.

### 11.2 Auto-paste is optional and conservative

Auto-paste must be disabled by default until it is proven reliable on the supported Windows applications.

When enabled, Wisper may paste only when:

- clipboard verification succeeded;
- the foreground/target context is consistent with the recording context, or another explicitly validated safe rule passes;
- no Wisper window has stolen focus;
- no processing state is still active.

If safe paste cannot be established:

- leave the text in the clipboard;
- do not force focus;
- do not simulate repeated clicks;
- show a short, non-blocking status that the text was copied but not pasted.

The paste adapter must use a bounded, simple Windows mechanism. It must not require a persistent accessibility automation engine or heavy background process.

---

## 12. Authoritative application state machine

Use one authoritative state machine:

```text
STARTING
  -> IDLE
  -> OPENING_AUDIO
  -> RECORDING
  -> STOPPING_AUDIO
  -> VALIDATING_AUDIO
  -> TRANSCRIBING
  -> FORMATTING_OR_TRANSLATING
  -> DELIVERING_TEXT
  -> IDLE

Any active state
  -> RECOVERABLE_ERROR
  -> IDLE

Application exit
  -> SHUTTING_DOWN
  -> TERMINATED
```

Rules:

- start is accepted only in IDLE;
- stop is accepted only in RECORDING;
- only one recording lifecycle may exist;
- UI controls render state but do not own it;
- duplicate toggle events do not create parallel operations;
- every transition is validated and logged;
- illegal transitions are rejected and tested;
- shutdown rejects new work;
- shutdown closes the active stream and releases resources within a bounded timeout.

---

## 13. Audio lifecycle

### 13.1 Single owner

One application service must be the only owner allowed to create, stop, or close capture streams.

Settings, device lists, diagnostics screens, and UI widgets must not own recording streams.

### 13.2 Capture format

Preferred behavior:

- capture mono float32;
- use the endpoint's supported native/default sample rate;
- commonly 44.1 kHz or 48 kHz;
- resample inside Wisper to the provider-required rate;
- preserve raw samples for validation;
- process a copy after validation;
- never normalize silence into fake speech;
- detect clipping and callback status conditions.

### 13.3 Open algorithm

1. Confirm state is IDLE.
2. Resolve the saved stable device identity.
3. Validate it is an input endpoint.
4. Read its supported native/default format.
5. Construct exactly one capture stream.
6. Start the stream.
7. Confirm activation.
8. Transition to RECORDING.

On failure:

- close any partially created stream in `finally`;
- detach references;
- map the error;
- enter a recoverable state;
- do not open another physical endpoint automatically.

### 13.4 Stop algorithm

1. Atomically transition to STOPPING_AUDIO.
2. Stop accepting new callback frames.
3. Stop the stream using a bounded timeout where supported.
4. Close the stream in `finally`.
5. Detach the stream reference.
6. Drain only frames for the current capture ID.
7. create immutable captured audio;
8. continue to validation.

Cleanup must be idempotent.

### 13.5 Bounded recording

- captured data must be bounded by a configurable maximum duration;
- a default maximum must prevent unbounded memory use;
- reaching the maximum must stop safely;
- callback queues must be bounded;
- queue overflow must become a warning or structured error;
- callback code must perform minimal work.

### 13.6 Audio result categories

Keep these outcomes distinct:

- NO_DEVICE;
- PERMISSION_DENIED;
- DEVICE_BUSY;
- DEVICE_DISCONNECTED;
- STREAM_ERROR;
- NO_AUDIO_FRAMES;
- TOO_SHORT;
- WEAK_SIGNAL;
- CLIPPED_SIGNAL;
- VALID_AUDIO.

WEAK_SIGNAL must never trigger device cycling, driver changes, Windows repair, or rapid reopen loops.

---

## 14. Minimal settings

The first stable version should expose only necessary settings.

### General

- selected microphone;
- refresh devices;
- test microphone;
- configured hotkey;
- auto-paste on/off;
- autostart on/off;
- maximum recording duration;
- launch floating button on startup.

### Language

- input language: Auto or selected language;
- output language: Same as input or selected language;
- safe punctuation/formatting on/off.

### Groq

- API key configured/not configured;
- transcription model;
- formatting/translation model;
- test connection.

### Diagnostics

- current device information;
- last capture metrics;
- last structured error;
- create support report;
- open logs folder;
- clear logs.

Do not expose dozens of tuning controls in the first stable version.

---

## 15. Recommended architecture

Use a `src` layout and dependency inversion, but keep the implementation smaller than the original specification.

```text
wisper/
├── pyproject.toml
├── README.md
├── docs/
│   ├── architecture.md
│   ├── audio-safety.md
│   ├── privacy.md
│   ├── troubleshooting.md
│   └── release-checklist.md
├── src/
│   └── wisper/
│       ├── __main__.py
│       ├── bootstrap.py
│       ├── domain/
│       │   ├── models.py
│       │   ├── errors.py
│       │   └── state.py
│       ├── application/
│       │   ├── ports.py
│       │   ├── dictation_service.py
│       │   ├── audio_session_service.py
│       │   └── delivery_service.py
│       ├── audio/
│       │   ├── device_catalog.py
│       │   ├── device_resolver.py
│       │   ├── capture_session.py
│       │   ├── signal_analysis.py
│       │   ├── processing.py
│       │   └── backend.py
│       ├── groq/
│       │   ├── client.py
│       │   ├── transcription.py
│       │   ├── text_transform.py
│       │   └── prompts.py
│       ├── platform/
│       │   ├── clipboard.py
│       │   ├── hotkeys.py
│       │   ├── focus_context.py
│       │   ├── autostart.py
│       │   ├── single_instance.py
│       │   └── windows/
│       ├── infrastructure/
│       │   ├── config.py
│       │   ├── secrets.py
│       │   ├── logging.py
│       │   └── paths.py
│       └── ui/
│           ├── controller.py
│           ├── floating_button.py
│           ├── settings_dialog.py
│           ├── diagnostics_dialog.py
│           └── tray.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── hardware/
│   └── fixtures/
├── scripts/
│   ├── run_checks.ps1
│   └── run_hardware_tests.ps1
└── packaging/
    └── windows/
```

Dependency direction:

```text
UI / platform / infrastructure / Groq adapters
                    |
                    v
             application services
                    |
                    v
                  domain
```

Rules:

- domain imports nothing from outer layers;
- application services depend on typed protocols;
- adapters translate library-specific errors into domain errors;
- UI sends intents and renders immutable state snapshots;
- bootstrap is the only composition root;
- no module-level creation of SDK clients, files, models, hotkeys, or audio streams;
- no monolithic controller owning UI, audio, network, configuration, and delivery logic;
- use typed requests, results, warnings, and errors instead of loose dictionaries.

---

## 16. Reliability and observability

- generate one correlation ID per dictation request;
- log state transitions and durations;
- use rotating logs with bounded total size;
- redact secrets and dictated text;
- never silently swallow exceptions;
- preserve tracebacks for unexpected errors;
- map expected failures to structured errors;
- apply bounded timeouts to network, shutdown, device opening, and platform actions;
- retry only transient, idempotent operations;
- no endless loops;
- no background watchdog unless it provides actionable value and shuts down cleanly;
- do not add telemetry in the first stable version.

---

## 17. Configuration and local data

Use Windows-appropriate per-user data directories, not the source tree.

Suggested files:

- `settings.json` for validated non-secret settings;
- `logs/wisper.log` for rotating privacy-safe logs;
- optional diagnostic exports created only by user action.

Requirements:

- version the settings schema;
- validate types, ranges, enums, and unknown fields;
- migrate schemas explicitly;
- write atomically through a temporary file and replace;
- preserve corrupt files for diagnostics instead of silently destroying them;
- recover with safe defaults;
- keep API keys in secure storage or environment variables;
- never store dictated text by default;
- never store audio recordings by default.

---

## 18. Accessibility requirements

- floating button must have an accessible name and description;
- settings must have predictable focus order;
- all functions must be operable without a physical keyboard where Windows accessibility mechanisms allow it;
- hotkey capture must work with the Windows On-Screen Keyboard for supported keys;
- do not rely on color alone;
- provide sufficient contrast;
- avoid tiny controls;
- avoid modal dialogs during normal dictation;
- keep the app usable with the Windows On-Screen Keyboard;
- never require drag-only interaction for a necessary setting;
- errors must explain what the user can do next.

---

## 19. Testing strategy

### 19.1 Unit tests

Cover at minimum:

- every legal and illegal state transition;
- duplicate toggle rejection;
- stable device identity resolution;
- ambiguous device resolution;
- open/stop/close idempotency;
- cleanup after failure at every audio lifecycle step;
- audio duration, RMS, peak, clipping, and weak-signal thresholds;
- resampling without mutation of raw audio;
- Groq timeout and error mapping;
- formatting and translation prompt behavior using mocked responses;
- rejection of meta-commentary or excessive rewrites;
- language selection rules;
- clipboard verification;
- safe auto-paste decision logic;
- hotkey validation rules;
- settings validation and migration;
- secret redaction;
- desktop shortcut and single-instance packaging logic where testable.

### 19.2 Contract and integration tests

Use fake adapters to assert:

- device enumeration creates zero streams;
- refreshing devices creates zero streams;
- one start creates one stream;
- one stop closes one stream;
- partial failures still close resources;
- late callback frames from an old capture are ignored;
- disconnect does not trigger endpoint scanning;
- concurrent toggles do not create parallel capture;
- UI does not own audio streams;
- shutdown releases all resources;
- Groq is attempted only for valid audio;
- formatting failure preserves the transcript;
- clipboard verification precedes paste.

Normal CI must not call the real Groq API.

### 19.3 Windows hardware tests

Hardware tests are manual or opt-in and never run on shared CI.

Required scenarios:

- built-in Realtek microphone;
- USB microphone or webcam microphone;
- Bluetooth headset microphone selected;
- Bluetooth headset present but not selected;
- device connection/disconnection between recordings;
- selected device disconnected during recording;
- Windows suspend/resume;
- 100 repeated short recordings;
- settings opened repeatedly between recordings;
- microphone test repeated several times;
- Groq timeout or outage;
- application exit while idle;
- application exit while recording;
- application exit while processing;
- floating-button click while cursor is in Notepad;
- floating-button click while cursor is in a browser text field;
- floating-button click while cursor is in another common desktop text field;
- physical keyboard hotkey;
- Windows On-Screen Keyboard hotkey;
- desktop shortcut first launch and repeated launch;
- single-instance behavior.

For each audio scenario, verify the microphone still works afterward in an independent application such as Windows Sound settings or Voice Recorder.

### 19.4 CI

CI must run:

```text
format check
lint
type check
unit tests
integration tests with fake adapters
package/import smoke test
```

Run the supported Python version matrix on Windows. Other operating systems may run platform-independent tests, but passing them must not be presented as real platform support.

---

## 20. Implementation phases

The agent must complete phases in order. It must not build optional convenience features before the safe audio and focus-preserving vertical slice works.

### Phase 0 — Inspect and preserve evidence

- inspect the current repository;
- preserve existing behavior notes, sanitized logs, and tests;
- identify reusable code without assuming it is correct;
- create a reference tag or branch if repository access allows it;
- identify current packaging and configuration behavior;
- write a short phase plan;
- do not reuse secrets or personal dictated content.

Exit condition: documented current-state inventory and risk list.

### Phase 1 — Domain, settings, and state machine

- create the `src` layout;
- implement typed models, errors, and state machine;
- implement settings schema and atomic storage;
- implement secret-storage interface;
- add unit tests;
- create the composition root skeleton.

Exit condition: all phase tests pass.

### Phase 2 — Safe microphone vertical slice

- implement metadata-only enumeration;
- implement stable Windows endpoint identity;
- implement manual microphone selection;
- implement single-owner audio lifecycle;
- implement raw audio statistics;
- implement internal resampling;
- implement microphone test;
- add fake-backend contracts;
- run repeated-capture hardware tests.

Exit condition: 100 repeated recordings pass on Windows hardware without degrading microphone behavior.

### Phase 3 — Floating button and focus preservation

- implement the always-on-top draggable microphone button;
- implement non-activating click behavior;
- implement visible states;
- preserve cursor focus in tested applications;
- store button position safely;
- implement single-instance behavior;
- add focus-context adapter and tests.

Exit condition: clicking the button starts/stops recording without stealing focus in the supported test applications.

### Phase 4 — Hotkeys and accessibility

- implement safe global hotkey registration;
- enforce forbidden single-key rules;
- support toggle behavior;
- test physical keyboard input;
- test Windows On-Screen Keyboard input;
- add accessible names, descriptions, focus order, and contrast.

Exit condition: supported hotkeys work from both physical and on-screen keyboards without interfering with ordinary typing.

### Phase 5 — Groq transcription

- implement secure API key handling;
- implement Groq transcription adapter;
- add timeouts, cancellation, bounded retries, and error mapping;
- send only validated audio;
- return typed results;
- add mocked integration tests;
- run a user-authorized real API smoke test.

Exit condition: speech reliably becomes raw text and failures return the app to IDLE.

### Phase 6 — Formatting, translation, and languages

- implement input/output language settings;
- implement the initial supported-language list after verifying Groq model support;
- implement conservative formatting;
- implement optional translation;
- implement final-output safety validation;
- ensure failures preserve raw transcription;
- add mocked tests for all critical rules.

Exit condition: same-language formatting and cross-language output work without commentary or unwanted rewriting.

### Phase 7 — Clipboard and optional auto-paste

- implement verified clipboard copy;
- implement conservative focus-context comparison;
- implement optional auto-paste;
- default auto-paste to off until hardware/manual validation passes;
- ensure copy-only fallback is always available;
- add integration and manual tests.

Exit condition: clipboard delivery is reliable, and auto-paste never knowingly targets an unrelated window.

### Phase 8 — Settings, diagnostics, tray, and support report

- finish the minimal settings UI;
- implement system tray actions;
- implement diagnostics view;
- implement privacy-safe support report;
- implement log opening and clearing;
- keep all blocking operations off the UI thread.

Exit condition: the user can configure the app and diagnose common failures without exposing secrets or dictated content.

### Phase 9 — Windows packaging

- create the installer;
- create the desktop shortcut automatically;
- create the Start menu entry;
- implement upgrade and uninstall behavior;
- validate data paths;
- validate single-instance behavior after installation;
- document installation and first run.

Exit condition: a clean Windows 11 install works from desktop shortcut through successful dictation.

### Phase 10 — Release hardening

- run the full automated suite;
- run the complete Windows hardware matrix;
- run 100 repeated recordings;
- verify microphone operation before and after tests in an independent app;
- inspect logs for secrets and dictated text;
- complete privacy, troubleshooting, architecture, and release documents;
- list residual risks honestly;
- do not claim unsupported platform support.

Exit condition: all Definition of Done items are supported by evidence.

---

## 21. Definition of Done

The agent may report completion only when:

- the application installs on Windows 11;
- the desktop shortcut is created automatically;
- launching the shortcut shows the floating microphone button;
- only one application instance runs;
- the button can be moved and its position is remembered;
- clicking it does not steal focus in the documented supported applications;
- first click starts recording;
- second click stops recording;
- button state visibly changes for ready, recording, processing, and error;
- a supported global hotkey performs the same toggle behavior;
- the hotkey works from the Windows On-Screen Keyboard;
- forbidden unmodified letters, digits, and ordinary punctuation cannot be assigned;
- the selected microphone remains stable across runtime index changes;
- Bluetooth microphones work when explicitly selected;
- device refresh opens zero streams;
- one recording opens exactly one stream and closes it exactly once;
- 100 repeated recordings do not leak streams, handles, threads, or unbounded memory;
- the application never changes Windows audio configuration;
- valid speech is transcribed through Groq;
- punctuation/formatting is conservative;
- selected-language translation works for verified supported languages;
- the model does not answer or comment on dictated content;
- clipboard copy is verified;
- auto-paste, when enabled, is conservative and falls back to clipboard-only;
- no API key is stored in plain-text settings or logs;
- logs do not contain full dictated text or clipboard contents;
- settings and diagnostics remain responsive;
- all automated checks pass;
- Windows hardware tests are documented with evidence;
- installation, first run, privacy behavior, and troubleshooting are documented;
- unsupported behavior and residual risks are explicitly stated.

---

## 22. Agent working rules

The coding agent must:

1. Read this entire specification before editing code.
2. Inspect the existing repository and tests.
3. Write a short plan before each implementation phase.
4. Make small, reviewable changes.
5. Add or update tests with each behavior change.
6. Run relevant checks during development and the full suite at phase completion.
7. Never hide a failing check.
8. Never weaken a test merely to make it pass.
9. Never claim hardware safety based only on mocks.
10. Never add a dependency without documenting why it is needed.
11. Prefer standard-library or well-established dependencies when practical.
12. Avoid adding modules that do not have a clear responsibility required by this specification.
13. Keep the product simple; do not add speculative features.
14. Clearly label automated results, hardware results, assumptions, and unverified behavior.
15. Continue autonomously through routine decisions.
16. Request user action only for permissions, secrets, hardware validation, destructive choices, or genuine requirement conflicts.
17. Never mutate Windows audio configuration.
18. Never silently broaden network or privacy behavior.
19. Never declare a phase complete without its exit condition.
20. At the end, produce a concise implementation report containing:
    - completed phases;
    - test results;
    - hardware evidence;
    - known limitations;
    - remaining risks;
    - exact steps for installation and use.

---

## 23. Required architectural decision records

Create short ADRs for:

- Windows audio backend choice;
- stable microphone identity strategy;
- threading and concurrency model;
- non-activating floating-button implementation;
- global hotkey implementation and On-Screen Keyboard behavior;
- Groq model selection and provider policy;
- secure API-key storage;
- focus-context and conservative auto-paste policy;
- Windows packaging approach;
- supported-platform policy.

Each ADR must contain:

- context;
- decision;
- alternatives considered;
- consequences;
- verification method.

---

## 24. Explicitly out of scope for the first stable version

- OpenAI integration;
- OpenRouter integration;
- additional translation APIs;
- local Whisper fallback;
- spell-checking modules;
- grammar-checking modules;
- style rewriting;
- text history;
- text-action buttons;
- arbitrary voice commands;
- continuous listening;
- background microphone probing;
- automatic gain control implemented by Wisper;
- Windows audio repair;
- driver management;
- account system;
- telemetry;
- cloud storage of recordings;
- plugin execution;
- arbitrary desktop automation;
- claims of full Linux or macOS support.

These features may be considered later only after the stable Windows version is proven.

---

## 25. Final product principle

Wisper succeeds when it quietly helps the user write.

The program must remain simple enough to understand and test. The microphone is a shared Windows resource, not something Wisper owns beyond one explicit recording session. The active text field belongs to another application, so Wisper must not casually steal focus or paste blindly.

Every implementation decision must preserve these boundaries:

- do not change Windows;
- do not switch microphones without permission;
- do not open more than one recording stream;
- do not interfere with ordinary typing;
- do not lose the user's cursor;
- do not over-process the user's words;
- do not add complexity without demonstrated value;
- fail safely and return to a usable state.
