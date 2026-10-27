param([string]$Python, [ValidateRange(1,65535)][int]$Port = 8781, [string]$PreparedData, [switch]$AllowPartial, [switch]$Check, [switch]$Open, [switch]$Restart)
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
if ($Restart) {
    # Stops ONLY a DÉCLIC server (uvicorn axis7.server:app) listening on this port, and its launcher.
    # Any other program on the port is left untouched and the restart is refused.
    $taskListeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    foreach ($taskListener in $taskListeners) {
        $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskListener.OwningProcess)"
        if (-not $taskProcess -or $taskProcess.CommandLine -notmatch 'axis7\.server:app') {
            throw "Le port $Port est utilisé par un autre programme que DÉCLIC ; rien n'a été arrêté. Choisissez un autre port avec -Port."
        }
        $taskParent = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskProcess.ParentProcessId)"
        Stop-Process -Id $taskProcess.ProcessId -Force
        if ($taskParent -and $taskParent.CommandLine -match 'axis7\.launch') { Stop-Process -Id $taskParent.ProcessId -Force -ErrorAction SilentlyContinue }
        Write-Host "Ancien serveur DÉCLIC arrêté (processus $($taskProcess.ProcessId))."
    }
    if ($taskListeners.Count) { Start-Sleep -Seconds 1 }
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
