$ErrorActionPreference = "Stop"
python -m ruff format --check .
python -m ruff check .
python -m mypy src
python -m pytest -m "not hardware"
python -c "import wispernext"
