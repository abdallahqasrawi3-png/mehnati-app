# مهنتي – Mehnaty

A platform for home businesses. Customers find home-made products and services; owners manage offers, orders, stock and costs; suppliers sell raw materials; deliveries are tracked. The interface is in Arabic and laid out right to left.

- **Backend:** Python 3.14 + Django 5.2 LTS + Django REST Framework, PostgreSQL 17 (`backend/`)
- **App:** React Native with Expo SDK 57. It runs in the browser and on Android (`mobile/`)
- **Docs:** [decisions](docs/DECISIONS.md) · [requirements, data model and API](docs/REQUIREMENTS.md) · [feature checklist](docs/FEATURES.md)

---

## Run everything with one command

From the project folder, in PowerShell:

```bash
.\start.bat
```

Add `-Demo` the first time to load demo data:

```bash
.\start.bat -Demo
```

The command:
1. starts PostgreSQL (on the first run it creates the database and `backend\.env` with random passwords),
2. sets up the Python environment and the app packages if they are missing,
3. applies migrations and reference data (cities, categories),
4. opens the API in a small window and the app in your browser.

| What | Where |
|------|-------|
| App (web) | http://localhost:8081 |
| API | http://localhost:8000/api/ (if 8000 is busy, the next free port; the console prints it) |
| Django admin | http://localhost:8000/admin/ (same port as the API) |
| Android | Install **Expo Go**, connect the phone to the same Wi-Fi, scan the QR code shown in the console |

Press **Ctrl+C** to stop the app and the API. PostgreSQL keeps running; to stop it: `scripts\stop_db.ps1`.

### Requirements (one-time)
- Python 3.12 or newer (3.14 used here)
- Node.js LTS: `winget install OpenJS.NodeJS.LTS`
- PostgreSQL binaries: `winget install PostgreSQL.PostgreSQL.17`. The script uses its own database folder in `%LOCALAPPDATA%\Mehnaty\pgdata`, so the installer's own database step is not needed.
- **Your own PostgreSQL server instead:** fill in `backend\.env` (copy `backend\.env.example`) and set `MEHNATY_EXTERNAL_DB=1` before running.

## Demo data (optional, clearly marked «[تجريبي]»)
`.\start.bat -Demo` creates demo accounts ending in `@demo.mehnaty.test`. They all share the password `DEMO_PASSWORD` defined in `backend/core/management/commands/seed_demo.py`.

The businesses and suppliers come from the table of Jenin home businesses in `backend/core/demo_data.py` (17 businesses, 7 sales channels/suppliers). Products and prices are illustrative and labelled «سعر تجريبي للعرض». No reviews are generated.

| Account | Role |
|---------|------|
| `customer@…`, `customer2@…` | customers |
| `owner01@…` … `owner17@…` | home-business owners, in the table's order (e.g. `owner02@…` = Emy Chocolate) |
| `supplier-sanabel@…`, `supplier-karim@…`, `supplier-bonbony@…`, `supplier-caramel@…`, `supplier-glass@…`, `supplier-needle@…`, `supplier-mad@…` | suppliers |
| `admin@…` | platform administrator |

To remove all demo data:
```bash
backend\.venv\Scripts\python.exe backend\manage.py seed_demo --remove
```

## Create an administrator
```bash
backend\.venv\Scripts\python.exe backend\manage.py createsuperuser
```
It asks for an email, full name and password. Sign in with that account at `/admin/`, or in the app (Account → لوحة مدير المنصة).

## Run the tests
The tests create a temporary test database. Run them on the local PostgreSQL (fast, offline) by setting `USE_LOCAL_DB=1` first, even when the app uses a cloud database:
```bash
$env:USE_LOCAL_DB = '1'
```
```bash
backend\.venv\Scripts\python.exe backend\manage.py test
```
The backend has 73 tests: accounts and addresses, permissions, catalog, search, orders, concurrent stock, shipping, reviews, reports and AI. The local PostgreSQL must be running; `scripts\setup_db.ps1` starts it.

Typecheck the app (from the `mobile` folder):
```bash
npx tsc --noEmit
```

## Configuration (`backend/.env`, see `.env.example`)
| Variable | Meaning |
|----------|---------|
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | Django basics (in production: DEBUG=false, real hosts, HTTPS) |
| `DATABASE_URL` | Cloud database such as Neon (`postgresql://…?sslmode=require`). When set, it is used instead of `DB_*`, and `start.bat` does not start a local PostgreSQL. Comment it out to go back to the local database. |
| `DB_*` | Local PostgreSQL connection (used when `DATABASE_URL` is not set) |
| `USE_LOCAL_DB=1` | Environment variable that forces the local database (for the tests) |
| `ANTHROPIC_API_KEY`, `AI_MODEL` | Optional Claude assistant. Without a key, the built-in rule-based assistant is used. |
| `SHIPPING_SIMULATOR_ENABLED` | Test-only fake carrier. Keep it `false`. |
| `MAX_IMAGE_UPLOAD_MB`, `CORS_ALLOWED_ORIGINS`, `JWT_*` | Uploads, allowed web origins, token lifetimes |

The app reads `EXPO_PUBLIC_API_URL` (full URL) or `EXPO_PUBLIC_API_PORT` to find the API. `start.bat` sets the port automatically.

## Manual setup (without the script)
```bash
cd backend
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py seed_reference
.venv\Scripts\python manage.py runserver 0.0.0.0:8000
```
Before `migrate`, edit `.env` with your database details. Then, in a second terminal:
```bash
cd mobile
npm ci
npx expo start --web
```

## Backups
```bash
"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -h localhost -U mehnaty -Fc mehnaty -f mehnaty.backup
```
Restore with `pg_restore -h localhost -U mehnaty -d mehnaty --clean mehnaty.backup`. Also back up `backend\media\` (uploaded images).

## Project layout
```
backend/   Django apps: accounts, core, catalog, suppliers, orders, inventory, shipping, reviews, notifications, reports, ai_assistant
mobile/    Expo app: src/screens (public, auth, cart, account, orders, business, supplier, admin), src/api, src/ui.tsx
scripts/   launch.ps1 (launcher), setup_db.ps1 (database), stop_db.ps1, diag.ps1 (setup check)
docs/      DECISIONS.md, REQUIREMENTS.md, FEATURES.md
start.bat               one-command launcher (runs scripts\launch.ps1)
```
