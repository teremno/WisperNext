# WisperNext

**Speak in one language. Insert polished text in another.**

WisperNext is a voice dictation and translation app for Windows. Speak naturally in English,
Ukrainian, or another supported language, then insert ready-to-use text in German, French,
Chinese, or any other language selected in Settings.

It combines speech recognition, translation, punctuation, capitalization, paragraph formatting,
and conservative correction of obvious recognition errors in one workflow.

![WisperNext voice-to-text translation workflow](docs/assets/wispernext-workflow.png)

## Two modes

Settings contain two independent options:

- **Spoken language** — the language you speak. Select a fixed language or automatic detection.
- **Final text language** — the language inserted at the cursor.

### Dictation without translation

```text
Spoken language: English
Final text language: Same as spoken language
```

Speak English and receive polished English text.

### Dictation with translation

```text
Spoken language: English
Final text language: German
```

Speak English and receive polished German text. The same workflow can translate Ukrainian into
English, French into Chinese, or any other configured language pair.

## How to use it

1. Place the cursor in a text field.
2. Press `F8` or click the floating microphone button.
3. Speak naturally.
4. Press `F8` or click the button again.
5. WisperNext recognizes, formats, optionally translates, and inserts the result.

`F8` is the default global hotkey. If another application already uses it, the floating button
remains available.

## Features

- separate spoken-language and final-text-language settings;
- same-language formatting or cross-language translation;
- 16 supported languages;
- automatic or manual microphone selection;
- optional automatic paste into the active field;
- floating button and global `F8` hotkey;
- English, Ukrainian, and Russian interface languages;
- secure Groq API-key storage in Windows Credential Manager;
- privacy-safe diagnostics without dictated text, audio, clipboard content, or API keys.

## Requirements

- Windows 10 or Windows 11 — currently tested on Windows 11;
- Python 3.12 or 3.13;
- Git;
- a [Groq API key](https://console.groq.com/keys).

A production installer is not available yet. The current version is installed from source.

## Install

Open PowerShell and run:

```powershell
git clone https://github.com/teremno/WisperNext.git
cd WisperNext

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

## Store the Groq API key

Create a key in the [Groq Console](https://console.groq.com/keys), then run:

```powershell
$secureKey = Read-Host "Enter your Groq API key" -AsSecureString
$env:WISPER_GROQ_API_KEY = [Net.NetworkCredential]::new("", $secureKey).Password

.\.venv\Scripts\python.exe .\scripts\migrate_groq_key_to_credential_manager.py

Remove-Item Env:WISPER_GROQ_API_KEY
```

The key is stored in Windows Credential Manager, not in application settings or diagnostic logs.

## Launch

```powershell
.\.venv\Scripts\pythonw.exe -m wispernext
```

After launch, use the floating button or `F8`. Right-click the floating button, or use the
system-tray icon, to open Settings.

Create a desktop shortcut with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\create_development_shortcut.ps1
```

## Development with an AI Coding Agent

This section is for contributors who want to modify WisperNext. An AI coding agent is not required to install or use the application.

1. Clone the repository.
2. Open the cloned `WisperNext` folder in an AI coding agent that can work with local files and Git.
3. Start a new task and send this instruction:

```text
Start with AGENT_START_PROMPT.md


**## Feedback and ideas

Feature requests, additional-language requests, bug reports, and new ideas are welcome. Contact
the author on X: **[S.O.V (@sovpoker)](https://x.com/sovpoker)**.

I am open to user feedback and will gladly consider useful requests whenever they are technically
possible and fit the project.

## Author

Created by **Oleksandr Smuryhin** in collaboration with OpenAI Codex.

WisperNext was built to remove the need to switch between separate dictation, translation, and
text-editing tools: speak naturally and receive polished text in the language you need.

Licensed under the [MIT License](LICENSE).
**
