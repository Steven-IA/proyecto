param()

$ErrorActionPreference = "Stop"

$agentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $agentDir ".env.local"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

if (-not $env:SENTINEL_API_URL) { $env:SENTINEL_API_URL = "http://localhost:8000" }
if (-not $env:AUTHORIZED_SUBNET) { $env:AUTHORIZED_SUBNET = "192.168.10.0/24" }

$exe = Join-Path $agentDir "dist\sentinel_agent.exe"
if (-not (Test-Path $exe)) {
    throw "No se encontró $exe. Construye el agente primero."
}

& $exe --daemon