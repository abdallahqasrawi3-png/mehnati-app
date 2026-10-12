<#
  Mehnaty - start everything with one command (from the project folder):   .\start.bat   or   .\start.bat -Demo

  What it does (safe to run every time):
    1. Starts the local PostgreSQL server (first run: creates the database and backend\.env)
    2. Creates the Python virtual environment and installs locked packages if missing
    3. Applies database migrations and reference data (cities, categories)
    4. Installs the app's npm packages if missing
    5. Starts the Django API (new window) and the Expo app (this window: web + QR code for Android)

  Options:
    -Demo     also load clearly-marked demo data (accounts, offers, orders)
    -NoWeb    start Expo without opening the browser
#>
param([switch]$Demo, [switch]$NoWeb)

$ErrorActionPreference = 'Continue'  # native tools write progress to stderr; we check exit codes instead
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Backend = Join-Path $Root 'backend'
$Mobile = Join-Path $Root 'mobile'
$Py = Join-Path $Backend '.venv\Scripts\python.exe'
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Green }
function Fail($msg) { Write-Host "`nERROR: $msg" -ForegroundColor Red; exit 1 }
function PortBusy([int]$p) { [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }

# ---------- tools
foreach ($tool in @('node', 'npm')) { if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { Fail "$tool is not installed. Install Node.js LTS: winget install OpenJS.NodeJS.LTS" } }
$PgBin = $env:MEHNATY_PG_BIN
if (-not $PgBin) {
  $PgBin = Get-ChildItem 'C:\Program Files\PostgreSQL' -Directory -ErrorAction SilentlyContinue |
    Sort-Object { [int]($_.Name -replace '\D', '') } -Descending | ForEach-Object { Join-Path $_.FullName 'bin' } |
    Where-Object { Test-Path (Join-Path $_ 'pg_ctl.exe') } | Select-Object -First 1
}
if (-not $PgBin) { Fail 'PostgreSQL is not installed. Install it: winget install PostgreSQL.PostgreSQL.17' }

# ---------- database
Step 'PostgreSQL'
& (Join-Path $Root 'scripts\setup_db.ps1') -PgBin $PgBin
if ($LASTEXITCODE -ne 0) { Fail 'Database setup failed (see messages above).' }

# ---------- backend
Step 'Python backend'
if (-not (Test-Path $Py)) {
  $launcher = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
  & $launcher -m venv (Join-Path $Backend '.venv')
  if ($LASTEXITCODE -ne 0) { Fail 'Could not create the Python virtual environment (Python 3.12+ required).' }
}
& $Py -c "import django, rest_framework, psycopg" 2>$null
if ($LASTEXITCODE -ne 0) {
  & $Py -m pip install --disable-pip-version-check -q -r (Join-Path $Backend 'requirements.txt')
  if ($LASTEXITCODE -ne 0) { Fail 'pip install failed.' }
}
Push-Location $Backend
try {
  & $Py manage.py migrate --noinput
  if ($LASTEXITCODE -ne 0) { Fail 'Migrations failed.' }
  & $Py manage.py seed_reference
  if ($Demo) { & $Py manage.py seed_demo }
} finally { Pop-Location }

# ---------- app
Step 'React Native (Expo) app'
if (-not (Test-Path (Join-Path $Mobile 'node_modules'))) {
  Push-Location $Mobile
  try { npm ci --no-audit --no-fund; if ($LASTEXITCODE -ne 0) { Fail 'npm ci failed.' } } finally { Pop-Location }
}

# ---------- run
# Another program may already use port 8000/8081: pick the first free ports and tell the app.
$ApiPort = if ($env:MEHNATY_API_PORT) { [int]$env:MEHNATY_API_PORT } else { 8000 }
while (PortBusy $ApiPort) { $ApiPort++ }
$WebPort = 8081
while (PortBusy $WebPort) { $WebPort++ }
$env:EXPO_PUBLIC_API_PORT = "$ApiPort"

Step "Starting the API on http://localhost:$ApiPort  (admin: http://localhost:$ApiPort/admin/)"
$api = Start-Process -FilePath $Py -ArgumentList 'manage.py', 'runserver', "0.0.0.0:$ApiPort", '--noreload' -WorkingDirectory $Backend -PassThru -WindowStyle Minimized

Step "Starting the app. Web: http://localhost:$WebPort   Android: scan the QR code with Expo Go (same Wi-Fi). Press Ctrl+C to stop."
Push-Location $Mobile
try {
  if ($NoWeb) { npx expo start --port $WebPort } else { npx expo start --web --port $WebPort }
} finally {
  Pop-Location
  if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue }
  Write-Host 'Stopped the API. (PostgreSQL keeps running; stop it with scripts\stop_db.ps1)' -ForegroundColor Yellow
}
