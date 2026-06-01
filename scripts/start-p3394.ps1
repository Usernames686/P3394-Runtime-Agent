$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ProjectDir = Join-Path $RepoRoot "local-demo"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python virtual environment not found: $Python"
}

$env:AGENTCLAW_PROJECT_DIR = $ProjectDir
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

& $Python -X utf8 -m agentclaw.cli serve `
    -d $ProjectDir `
    --host 127.0.0.1 `
    --port 8000
