# Registra el supervisor local como tarea programada del usuario actual (al iniciar sesión).
# Instalar:   powershell -ExecutionPolicy Bypass -File scripts\install-supervisor.ps1
# Quitar:     powershell -ExecutionPolicy Bypass -File scripts\install-supervisor.ps1 -Remove
param([switch]$Remove)
$name = 'ERPEC Supervisor'
if ($Remove) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Tarea '$name' eliminada"
    return
}
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv\Scripts\pythonw.exe'
$script = Join-Path $root 'scripts\supervisor-windows.py'
$action = New-ScheduledTaskAction -Execute $python -Argument "`"$script`"" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Description 'Mantiene PostgreSQL y las instancias Odoo de ERP EC activas' -Force | Out-Null
Start-ScheduledTask -TaskName $name
Write-Output "Tarea '$name' registrada y en ejecución"
