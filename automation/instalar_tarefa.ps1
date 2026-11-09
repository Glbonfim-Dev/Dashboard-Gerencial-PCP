[CmdletBinding()]
param(
    [string]$Excel = '\\srvdc01\dados\PUBLICO\PCP\CONTROLE GRID - PRAZOS\EDEMIR\Melhorias - Faturamento moldes 2026.xlsx'
)

$ErrorActionPreference = 'Stop'
$taskName = 'Dashboard Gerencial - Atualizar Site'
$projectDir = Split-Path -Parent $PSScriptRoot
$monitor = Join-Path $projectDir 'monitorar_excel.py'
$pythonLauncher = Join-Path $env:LOCALAPPDATA 'Programs\Python\Launcher\py.exe'

if (-not (Test-Path -LiteralPath $pythonLauncher)) {
    throw "Python Launcher nao encontrado em: $pythonLauncher"
}
$pythonExe = (& $pythonLauncher -3 -c 'import sys; print(sys.executable)').Trim()
$pythonw = Join-Path (Split-Path -Parent $pythonExe) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) {
    throw "Python sem janela nao encontrado em: $pythonw"
}
if (-not (Test-Path -LiteralPath $monitor)) {
    throw "Monitor nao encontrado em: $monitor"
}
if (-not (Test-Path -LiteralPath $Excel)) {
    throw "Excel compartilhado nao encontrado ou sem permissao: $Excel"
}

$arguments = '"{0}" "{1}"' -f $monitor, $Excel
$action = New-ScheduledTaskAction `
    -Execute $pythonw `
    -Argument $arguments `
    -WorkingDirectory $projectDir
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 1)
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal `
    -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description 'Detecta salvamentos no Excel compartilhado e publica os dados do Dashboard Gerencial.' `
    -Force | Out-Null

Write-Output "Tarefa instalada: $taskName"
Write-Output "Excel monitorado: $Excel"
Write-Output "Execucao silenciosa: $pythonw"
Write-Output 'A tarefa sera executada a cada 1 minuto enquanto este usuario estiver conectado.'
