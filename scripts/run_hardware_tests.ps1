$ErrorActionPreference = "Stop"
python -m pytest -m hardware -v
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
