param([ValidateSet('backend','test','record','samples','check','setup')][string]$Task = 'backend')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if ($Task -eq 'setup') {
    if (-not (Test-Path -LiteralPath $taskPython)) {
        py -3.11 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.11 or newer, then create .venv first.' }
    }
    & $taskPython -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $taskPython -m pip install -r requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $taskPython -m pip install --no-deps -e .
    exit $LASTEXITCODE
}
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run ./dev.ps1 setup first.' }
switch ($Task) {
    'backend' { & $taskPython -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 }
    'test' { & $taskPython -m pytest -q }
    'samples' { & $taskPython -m backend.tools.make_samples }
    'check' {
        & $taskPython -m compileall -q backend
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & $taskPython -m ruff check backend
    }
    'record' {
        & $taskPython -m backend.tools.record --scenario a --speed 10 --out frontend/public/replay_a.jsonl
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & $taskPython -m backend.tools.record --scenario b --speed 10 --out frontend/public/replay_b.jsonl
    }
}
exit $LASTEXITCODE
