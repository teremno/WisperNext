# Contributing to WisperNext

Start with the [Windows installation guide](docs/INSTALL_WINDOWS.md).
For the module boundaries, read [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Development environment

From the repository folder, install the development tools into the same environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Run the checks used by CI before proposing a change:

```powershell
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pytest -m "not hardware"
```

Hardware checks require a separate Windows session with a microphone. State which
checks you ran and which remain unverified.

## Working with a coding agent

Open the cloned repository in an agent that can work with local files and Git.
Start with this instruction:

```text
Start with AGENT_START_PROMPT.md
```

The [agent entry point](AGENT_START_PROMPT.md) links to the project rules.
Keep changes focused and preserve existing dictation controls and accessibility behavior.
Keep API keys, private dictation, and clipboard contents out of commits and logs.

## Documentation graphics

The README workflow uses `docs/assets/wispernext-workflow.png` for display and a
matching vector version at `docs/assets/wispernext-workflow.svg`. Keep labels and example
text consistent when changing either file. The graphic is an illustration, not an
application screenshot.
