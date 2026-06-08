<#
.SYNOPSIS
    Start the Fraud Detection durable-workflow demo on Windows.

.DESCRIPTION
    Starts the four local services in the correct order with health gating:
        1. MCP server        (port 8000)
        2. DTS worker        (no port - pulls from DTS)
        3. Backend (BFF)     (port 8001)
        4. React UI          (port 3000)

    The Azure Durable Task Scheduler is expected to be reachable already
    (either the local Docker emulator on :8080 or an Azure DTS endpoint set
    via DTS_ENDPOINT in .env). This script does NOT start the emulator.

    Each service runs in its own window and logs to .\logs\<service>.log.
    Forces UTF-8 so emoji/unicode in logs never crash on Windows cp1252.

.PARAMETER StartEmulator
    Also start the local DTS emulator in Docker (port 8080/8082) before the
    other services. Requires Docker Desktop running.

.EXAMPLE
    .\start.ps1
.EXAMPLE
    .\start.ps1 -StartEmulator
#>
[CmdletBinding()]
param(
    [switch]$StartEmulator
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $here '..\..\..')).Path
$mcpDir = Join-Path $repoRoot 'mcp'
$uiDir = Join-Path $here 'ui'
$logDir = Join-Path $here 'logs'

# Force UTF-8 for any child process we spawn from here.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    [ok] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "    [!!] $msg" -ForegroundColor Yellow }

function Wait-Port {
    param([int]$Port, [int]$TimeoutSec = 60, [string]$Name = "service")
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $ok = Test-NetConnection -ComputerName localhost -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($ok) { Write-Ok "$Name listening on port $Port"; return $true }
        Start-Sleep -Seconds 2
    }
    Write-Warn2 "$Name did not open port $Port within $TimeoutSec s (check $logDir)"
    return $false
}

function Start-Service2 {
    param([string]$Title, [string]$WorkDir, [string]$Command, [string]$LogFile)
    # Launch in a new window so the presenter can see each service; tee to a log.
    $full = "`$env:PYTHONUTF8='1'; `$env:PYTHONIOENCODING='utf-8'; Set-Location '$WorkDir'; $Command *>&1 | Tee-Object -FilePath '$LogFile'"
    Start-Process -FilePath 'powershell.exe' `
        -ArgumentList @('-NoExit', '-NoProfile', '-Command', $full) `
        -WindowStyle Normal | Out-Null
    Write-Ok "$Title started (logs: $LogFile)"
}

Write-Host ""
Write-Host "Fraud Detection Durable Workflow - Demo Launcher" -ForegroundColor White
Write-Host "------------------------------------------------" -ForegroundColor DarkGray

# 0) Optional: local DTS emulator
if ($StartEmulator) {
    Write-Step "Starting local DTS emulator (Docker)"
    try {
        docker rm -f dts-emulator 2>$null | Out-Null
        docker run -d --name dts-emulator -p 8080:8080 -p 8082:8082 `
            mcr.microsoft.com/dts/dts-emulator:latest | Out-Null
        Wait-Port -Port 8080 -TimeoutSec 60 -Name "DTS emulator" | Out-Null
        Write-Ok "DTS emulator dashboard: http://localhost:8082"
    } catch {
        Write-Warn2 "Could not start DTS emulator: $_"
        Write-Warn2 "Is Docker Desktop running? Or use an Azure DTS endpoint in .env."
    }
} else {
    Write-Step "Using DTS endpoint from .env (no local emulator)"
    Write-Warn2 "If you intended the local emulator, re-run with -StartEmulator"
}

# 1) MCP server
Write-Step "Starting MCP server (port 8000)"
Start-Service2 -Title 'MCP' -WorkDir $mcpDir `
    -Command 'uv run python mcp_service.py' `
    -LogFile (Join-Path $logDir 'mcp.log')
Wait-Port -Port 8000 -TimeoutSec 60 -Name 'MCP' | Out-Null

# 2) Worker
Write-Step "Starting DTS worker"
Start-Service2 -Title 'Worker' -WorkDir $here `
    -Command 'uv run python worker.py' `
    -LogFile (Join-Path $logDir 'worker.log')
Write-Ok "Worker launched (connects to DTS; no local port)"
Start-Sleep -Seconds 8

# 3) Backend
Write-Step "Starting backend (port 8001)"
Start-Service2 -Title 'Backend' -WorkDir $here `
    -Command 'uv run python backend.py' `
    -LogFile (Join-Path $logDir 'backend.log')
Wait-Port -Port 8001 -TimeoutSec 60 -Name 'Backend' | Out-Null

# 4) React UI
Write-Step "Starting React UI (port 3000)"
Start-Service2 -Title 'UI' -WorkDir $uiDir `
    -Command 'npm run dev' `
    -LogFile (Join-Path $logDir 'ui.log')
Wait-Port -Port 3000 -TimeoutSec 90 -Name 'UI' | Out-Null

Write-Host ""
Write-Step "Verifying backend readiness (/health)"
try {
    $health = Invoke-RestMethod -Uri 'http://localhost:8001/health' -TimeoutSec 15
    Write-Ok ("Backend health: {0}" -f $health.status)
    foreach ($k in $health.checks.PSObject.Properties.Name) {
        $c = $health.checks.$k
        if ($c.ok) { Write-Ok "  $k OK" } else { Write-Warn2 "  $k FAILED: $($c.error)" }
    }
} catch {
    Write-Warn2 "Could not reach /health yet: $_"
}

Write-Host ""
Write-Host "Demo is up. Open:  http://localhost:3000" -ForegroundColor Green
Write-Host "Ambient feed starts OFF - press the power button in the Live Feed panel," -ForegroundColor Gray
Write-Host "or POST http://localhost:8001/api/producer/start to begin Scenario 1." -ForegroundColor Gray
Write-Host "Stop everything with:  .\stop.ps1" -ForegroundColor Gray
Write-Host ""
