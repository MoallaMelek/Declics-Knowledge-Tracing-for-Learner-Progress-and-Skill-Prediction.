param([string]$Python, [ValidateRange(1,65535)][int]$Port = 8781, [string]$PreparedData, [switch]$AllowPartial, [switch]$Check, [switch]$Open)
$ErrorActionPreference = 'Stop'
$taskCommon = & git -C $PSScriptRoot rev-parse --path-format=absolute --git-common-dir 2>$null
$taskPrimary = if ($LASTEXITCODE -eq 0) { Split-Path -Parent $taskCommon } else { $PSScriptRoot }
$taskCandidates = @()
if ($Python) { $taskCandidates = @($Python) }
elseif ($env:DECLIC_PYTHON) { $taskCandidates = @($env:DECLIC_PYTHON) }
else {
    $taskCandidates = @((Join-Path $PSScriptRoot '.venv\Scripts\python.exe'), (Join-Path $taskPrimary '.venv\Scripts\python.exe'), (Join-Path $taskPrimary '..\..\work\.venv\Scripts\python.exe'))
    $taskSystem = Get-Command python -ErrorAction SilentlyContinue
    if ($taskSystem) { $taskCandidates += $taskSystem.Source }
}
$taskPython = $taskCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $taskPython) { throw 'Python/environnement introuvable. Préparez .venv selon docs/START_WINDOWS.md ou passez -Python chemin\python.exe.' }
$taskPython = (Resolve-Path -LiteralPath $taskPython).Path
& $taskPython -X utf8 -c "import sys; assert sys.version_info >= (3,12), 'Python 3.12+ requis'; import torch,fastapi,uvicorn,numpy,pydantic; print('Interpréteur vérifié :',sys.executable)"
if ($LASTEXITCODE -ne 0) { throw 'Python incompatible ou dépendances manquantes. Aucun paquet installé automatiquement ; voir docs/START_WINDOWS.md.' }
if (-not $PreparedData) {
    $taskLocalData = Join-Path $PSScriptRoot 'runtime\musical-demo'
    $taskSharedData = Join-Path $taskPrimary 'runtime\musical-demo'
    $PreparedData = if (Test-Path -LiteralPath $taskLocalData) { $taskLocalData } else { $taskSharedData }
}
$taskArgs = @('-X','utf8','-B','-m','axis7.launch','--port',"$Port",'--prepared-data',$PreparedData)
if ($AllowPartial) { $taskArgs += '--allow-partial' }
if ($Check) { $taskArgs += '--check' }
if ($Open) { $taskArgs += '--open' }
$taskPreviousPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $PSScriptRoot + [IO.Path]::PathSeparator + $taskPreviousPath
    & $taskPython @taskArgs
    if ($LASTEXITCODE -ne 0) { throw "Démarrage DÉCLIC refusé (code $LASTEXITCODE). Consultez le diagnostic ci-dessus." }
} finally { $env:PYTHONPATH = $taskPreviousPath }
