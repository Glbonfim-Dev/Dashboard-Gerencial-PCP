[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$taskName = 'Dashboard Gerencial - Atualizar Site'
$tarefa = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $tarefa) {
    Write-Output "A tarefa nao esta instalada: $taskName"
    exit 0
}

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Output "Tarefa removida: $taskName"
