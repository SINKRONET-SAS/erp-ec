param(
  [Parameter(Mandatory=$true)][string]$Python,
  [string]$PostgresBin = 'C:\Program Files\PostgreSQL\17\bin'
)
$ErrorActionPreference = 'Stop'
$erpRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $erpRoot
$upstream = Get-Content -LiteralPath upstream.json -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath "$PostgresBin\pg_ctl.exe")) { throw 'PostgreSQL 17 no está instalado en la ruta indicada.' }
if (-not (Test-Path -LiteralPath '.cache\odoo-community\.git')) {
  git clone --depth 1 --branch $upstream.branch --single-branch $upstream.repository .cache/odoo-community
  if ($LASTEXITCODE -ne 0) { throw 'Falló la descarga oficial.' }
}
$revision = git -C .cache/odoo-community rev-parse HEAD
if ($revision -ne $upstream.commit) {
  git -C .cache/odoo-community fetch --depth 1 origin $upstream.commit
  if ($LASTEXITCODE -ne 0) { throw 'No se pudo obtener la revisión fijada.' }
  git -C .cache/odoo-community checkout --detach $upstream.commit
  if ($LASTEXITCODE -ne 0) { throw 'No se pudo fijar la revisión; revisar cambios locales.' }
}
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
  & $Python -m venv .venv
  if ($LASTEXITCODE -ne 0) { throw 'Falló la creación del entorno Python.' }
}
& .venv/Scripts/python.exe -m pip install -r requirements-windows.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }
& .venv/Scripts/python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependencias incompatibles.' }
$env:ERPEC_PG_BIN = $PostgresBin
& .venv/Scripts/python.exe scripts/audit-community.py
if ($LASTEXITCODE -ne 0) { throw 'No pasó la auditoría Community.' }
Write-Output 'Entorno preparado. Para crear el piloto nuevo: .venv/Scripts/python.exe scripts/windows-local.py bootstrap'
