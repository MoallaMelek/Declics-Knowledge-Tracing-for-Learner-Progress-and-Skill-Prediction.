$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    $taskPython = Join-Path $PSScriptRoot '..\..\work\.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Create the Python environment using the instructions in README.md first.'
}
Write-Host 'DÉCLIC is available at http://127.0.0.1:8767/ while this window stays open.'
& $taskPython -m uvicorn axis7.server:app --host 127.0.0.1 --port 8767
