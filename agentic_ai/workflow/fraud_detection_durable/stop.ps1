<#
.SYNOPSIS
    Stop all Fraud Detection durable-workflow demo services on Windows.

.DESCRIPTION
    Finds and stops the demo processes started by start.ps1:
        - MCP server   (mcp_service.py)
        - DTS worker   (worker.py)
        - Backend      (backend.py)
        - React UI     (vite / npm run dev on port 3000)

    Matches by command line so it won't touch unrelated python/node processes.

.PARAMETER StopEmulator
    Also stop+remove the local DTS emulator Docker container.

.EXAMPLE
    .\stop.ps1
.EXAMPLE
    .\stop.ps1 -StopEmulator
#>
[CmdletBinding()]
param(
    [switch]$StopEmulator
)

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    [ok] $msg" -ForegroundColor Green }

# Match the demo processes by their command line (avoids killing the editor,
# Copilot, or other python/node processes).
$patterns = @(
    'mcp_service\.py',
    'worker\.py',
    'backend\.py',
    'fraud_detection_durable\\ui',   # vite / npm dev server for the UI
    'vite'
)

Write-Step "Stopping demo services"
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='node.exe'" |
    Where-Object {
        $cl = $_.CommandLine
        $cl -and ($patterns | Where-Object { $cl -match $_ }) -and ($cl -match 'fraud_detection_durable' -or $cl -match 'mcp_service\.py')
    }

if (-not $procs) {
    Write-Ok "No running demo services found."
} else {
    foreach ($p in $procs) {
        try {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
            Write-Ok ("Stopped PID {0} ({1})" -f $p.ProcessId, ($p.CommandLine -replace '.*\\', '').Substring(0, [Math]::Min(40, ($p.CommandLine -replace '.*\\', '').Length)))
        } catch {
            Write-Host "    [!!] Could not stop PID $($p.ProcessId): $_" -ForegroundColor Yellow
        }
    }
}

# Free any lingering listeners on the demo ports.
foreach ($port in @(8000, 8001, 3000)) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        try {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop
            Write-Ok "Freed port $port (PID $($c.OwningProcess))"
        } catch { }
    }
}

if ($StopEmulator) {
    Write-Step "Stopping local DTS emulator"
    try {
        docker rm -f dts-emulator 2>$null | Out-Null
        Write-Ok "DTS emulator removed"
    } catch {
        Write-Host "    [!!] Could not remove emulator: $_" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "All demo services stopped." -ForegroundColor Green
