$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonw = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"
if (-not (Test-Path -LiteralPath $pythonw -PathType Leaf)) {
    throw "WisperNext virtual environment was not found: $pythonw"
}

$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
if ([string]::IsNullOrWhiteSpace($desktop) -or -not (Test-Path -LiteralPath $desktop -PathType Container)) {
    throw "The current Windows desktop folder could not be resolved."
}

$shortcutPath = Join-Path $desktop "WisperNext.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = "-m wispernext"
$shortcut.WorkingDirectory = $projectRoot
$shortcut.Description = "WisperNext voice dictation"
$shortcut.IconLocation = "$pythonw,0"
$shortcut.Save()

if (-not (Test-Path -LiteralPath $shortcutPath -PathType Leaf)) {
    throw "The WisperNext desktop shortcut was not created."
}

[pscustomobject]@{
    Shortcut = $shortcutPath
    Target = $pythonw
    WorkingDirectory = $projectRoot
} | ConvertTo-Json
