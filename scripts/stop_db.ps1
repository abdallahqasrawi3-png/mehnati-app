# Stops the local PostgreSQL cluster started by start.ps1.
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine')
$PgBin = Get-ChildItem 'C:\Program Files\PostgreSQL' -Directory -ErrorAction SilentlyContinue |
  Sort-Object { [int]($_.Name -replace '\D', '') } -Descending | ForEach-Object { Join-Path $_.FullName 'bin' } |
  Where-Object { Test-Path (Join-Path $_ 'pg_ctl.exe') } | Select-Object -First 1
& (Join-Path $PgBin 'pg_ctl.exe') -D (Join-Path $env:LOCALAPPDATA 'Mehnaty\pgdata') stop
