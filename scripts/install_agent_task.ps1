param(
    [string]$TaskName = "SentinelAI Agent",
    [string]$AgentPath = ""
)

if (-not $AgentPath) {
    $AgentPath = Join-Path (Split-Path -Parent $PSScriptRoot) "agent\run_daemon.ps1"
}

if (-not (Test-Path $AgentPath)) {
    throw "No se encontró el script del agente: $AgentPath"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$AgentPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Host "Tarea '$TaskName' creada. El agente se iniciará al iniciar sesión."