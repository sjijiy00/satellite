param(
    [string]$TargetPane = '1:0.0'
)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskLogDirectory = Join-Path $taskRoot 'logs'
New-Item -ItemType Directory -Path $taskLogDirectory -Force | Out-Null
$taskLogPath = Join-Path $taskLogDirectory 'tmux-init-leader.log'
$taskTmux = (Get-Command tmux -ErrorAction Stop).Source
$taskDeadline = (Get-Date).AddMinutes(2)
Set-Content -LiteralPath $taskLogPath -Encoding UTF8 -Value 'Waiting for leader to become idle.'
Start-Sleep -Seconds 4

while ((Get-Date) -lt $taskDeadline) {
    $taskScreen = (& $taskTmux capture-pane -p -t $TargetPane 2>&1) -join "`n"
    if ($LASTEXITCODE -ne 0) {
        Add-Content -LiteralPath $taskLogPath -Encoding UTF8 -Value 'Target pane unavailable. No command sent.'
        exit 1
    }
    if ($taskScreen -match '(?im)^\s*[•·]\s+Working\b|esc to interrupt') {
        Start-Sleep -Seconds 2
        continue
    }
    if ($taskScreen -notmatch 'Ask Codex to do anything') {
        Start-Sleep -Seconds 2
        continue
    }
    & $taskTmux send-keys -t $TargetPane -l '/init'
    if ($LASTEXITCODE -ne 0) { exit 1 }
    Start-Sleep -Milliseconds 500
    & $taskTmux send-keys -t $TargetPane Enter
    Start-Sleep -Milliseconds 700
    $taskAfter = (& $taskTmux capture-pane -p -t $TargetPane 2>&1) -join "`n"
    if ($taskAfter -match '(?m)^\s*›\s*/init\s*$') {
        & $taskTmux send-keys -t $TargetPane Enter
    }
    Add-Content -LiteralPath $taskLogPath -Encoding UTF8 -Value 'Sent /init to idle leader pane. Completion must be verified in that pane.'
    exit 0
}

Add-Content -LiteralPath $taskLogPath -Encoding UTF8 -Value 'Timed out waiting for idle leader. No command sent.'
exit 1
