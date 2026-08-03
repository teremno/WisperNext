$ErrorActionPreference = "Stop"

function Invoke-PythonChecked {
    & python @args
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Invoke-PythonChecked -m ruff format --check .
Invoke-PythonChecked -m ruff check .
Invoke-PythonChecked -m mypy src
Invoke-PythonChecked -m pytest -m "not hardware"
Invoke-PythonChecked -c "import wispernext"
