$root = Split-Path -Parent $PSScriptRoot
$paths = @(
  'backend\.venv\Scripts\python.exe', 'backend\.env', 'backend\requirements.txt',
  'backend\accounts\migrations\0001_initial.py', 'backend\catalog\migrations\0001_initial.py',
  'backend\media', 'mobile\node_modules', 'mobile\package-lock.json', 'mobile\assets\icon.png', 'scripts\launch.ps1'
)
foreach ($p in $paths) { '{0,-48} {1}' -f $p, (Test-Path (Join-Path $root $p)) }
'pgdata PG_VERSION                                ' + (Test-Path (Join-Path $env:LOCALAPPDATA 'Mehnaty\pgdata\PG_VERSION'))
'postgres.exe bin                                 ' + (Test-Path 'C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe')
'node                                             ' + [bool](Get-Command node -ErrorAction SilentlyContinue)
