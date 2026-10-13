# Decisions (DECISIONS.md)

Answers from the owner (2026-10-12) and the technical choices made. Change any rule here and in the code together.

## Owner answers

| # | Question | Answer |
|---|----------|--------|
| 1 | First-release scope | **Full scope**: discovery + suppliers/raw materials, sales and purchase orders, stock, manual shipments, reviews, notifications, reports, AI. |
| 2 | Platforms / admin | **Web + Android** from one Expo React Native app (web via react-native-web, Android via Expo Go). Administration = **Arabic Django admin** + an in-app admin dashboard. iOS is not verified. |
| 3–6 | Business rules | **Use the proposed defaults** below. |
| 7 | Delivery / AI providers | No carrier or credentials supplied → manual shipment entry. AI = Claude API **if** a key is set, otherwise the built-in rule-based assistant. |
| – | Tooling | Install Node.js and PostgreSQL system-wide with winget. |

## Business rules (proposed defaults, approved)

**Accounts**
- Registration needs no approval. Administrators can suspend accounts (`is_active`) and business/supplier profiles (`status`).
- One account can be customer + home-business owner + supplier. Every account is a customer; the other roles exist when the matching profile exists. Data and permissions are separated per role.
- Sign-in uses email + password (Django password hashing). The API uses JWT (short access token + rotating refresh token with blacklist).

**Currency, places and contact**
- Currency: Israeli shekel (₪, ILS). Seed cities: Palestinian cities with sample areas, all editable in the admin.
- Public location = city/area only. Exact addresses are private: visible only to their owner and, as an order snapshot, to the seller of that order.
- Addresses can be specific (added 2026-10-13, for business owners receiving material deliveries at a workshop or storage room, and for customers):
  - Structured parts: street, building, floor, apartment/shop, nearest landmark, extra details. At least one of street / landmark / details is required.
  - Optional exact map pin, either from "use my current location" (`expo-location`, one-time, foreground only, never tracked) or pasted from a Google Maps link or coordinates. Stored rounded to 6 decimals (~10 cm); both values or neither; (0,0) and out-of-range values are rejected.
  - Orders copy the full text, landmark and pin when created, so later edits to a saved address never change an existing order. The seller or supplier gets a Google Maps link.
  - No map SDK or API key is used: the pin opens in the phone's or browser's map app.
- Public phone/WhatsApp appear only when the owner ticks the consent box. Otherwise customers contact the business through orders.

**Offers**
- Three offer types: `ready` (stock-tracked), `made_to_order` (no stock), `service` (no stock, optional preferred date and duration).
- Deleting an offer or material is a **soft delete**: it disappears from browsing, existing orders keep their snapshots and continue normally.
- `unit_cost` is private (reports only).

**Sales orders** (one home business per order). Pay on pickup or delivery. There is **no online payment** and no fake payment confirmation.

| From | To | Who |
|------|----|-----|
| pending | accepted, rejected | seller |
| pending | cancelled | customer or seller |
| accepted | preparing, cancelled | seller |
| preparing | ready, cancelled | seller |
| ready | in_transit (delivery only), completed (pickup only), cancelled | seller |
| in_transit | completed, delivery_failed | seller |
| delivery_failed | in_transit (retry), cancelled | seller |

- Customers may cancel **only while pending**. The seller marks completion.
- Stock for `ready` offers is reserved when the order is created. It is released on rejected/cancelled and turned into a sale on completed.

**Purchase orders** (business owner → one supplier per order)

| From | To | Who |
|------|----|-----|
| pending | accepted, rejected | supplier |
| pending | cancelled | buyer or supplier |
| accepted | preparing, cancelled | supplier |
| preparing | shipped, cancelled | supplier |
| shipped | received | buyer |

- Quantity must be ≥ the material's minimum purchase. Material stock is reserved at creation, released on rejected/cancelled, and deducted when **shipped** (goods leave the supplier). Supplier revenue counts when the buyer confirms **received**.

**Delivery**
- The seller sets the delivery fee per order, who pays it (buyer or seller) and whether it is **estimated or final**. A supplier's profile delivery cost is copied as an *estimate* into new purchase orders.
- Shipments are entered manually (carrier name, tracking number, status, cost, ETA). There is one shipment per order. Retries return the existing shipment (no duplicates).
- Carrier integration layer: adapters declare their capabilities. `SimulatorAdapter` exists **for tests only** (`SHIPPING_SIMULATOR_ENABLED`), is never presented as a real carrier, and is off by default. A shipment is marked `external_confirmed` only after the carrier adapter confirms it.

**Reviews**
- One review per **completed** sales order, rating 1–5 for the overall experience plus an optional comment. Only that order's customer can write it, and they may edit it later.
- Business owners cannot edit or delete reviews. Anyone signed in can report content. Admins resolve reports (hide a review, suspend a profile, hide an offer/material, or dismiss).

**Reports**
- Estimated operating profit = completed-order revenue − recorded cost of sold items − recorded direct expenses − delivery fees paid by the business.
- Items without a recorded cost are counted and the result is labelled incomplete.
- Raw-material purchases are shown separately and never deducted automatically. Owners record consumed materials as an expense (category "مواد مستهلكة").
- Supplier figures are separate from business figures.
- No platform commission was introduced.

**Notifications**: in-app only, written after the database commit (`transaction.on_commit`) and wrapped in try/except, so a failed notification never loses an order.

## Technical decisions

- **Django 5.2 LTS** (5.2.18) on **Python 3.14**, DRF 3.16, SimpleJWT 5.5, psycopg 3.3, PostgreSQL 17. All versions are locked in `backend/requirements.txt`.
- **Expo SDK 57** (React Native 0.86, React 19.2), React Navigation 7, locked in `mobile/package-lock.json`. Packages were installed with `npx expo install` so the versions match the SDK.
- **RTL**: `forcesRTL` in `app.json` + `I18nManager.forceRTL`, `dir="rtl"` on the web document. If a phone still reports LTR (Expo Go SDK 57 may ignore the setting), shared components flip rows and alignment (`FLIP` in `src/ui.tsx`).
- **PostgreSQL cluster**: the EDB installer's `initdb` step failed on this Windows machine (locale problem). The app therefore uses its own user-owned cluster in `%LOCALAPPDATA%\Mehnaty\pgdata` (locale C, UTF-8), created and started by `scripts/setup_db.ps1`. No admin rights are needed after PostgreSQL's binaries are installed.
- **Cloud database (2026-10-13)**: the owner moved the app to a Neon PostgreSQL database (eu-central-1, pooled endpoint).
  - The connection string lives only in `backend/.env` as `DATABASE_URL`, and `settings.py` parses it.
  - Pooled hosts disable server-side cursors (PgBouncer transaction mode) and keep persistent connections (`CONN_MAX_AGE=60`, with health checks); reconnecting per request cost 1.5–5 s.
  - Local data, including the owner's admin account and the demo data, was copied with `dumpdata`/`loaddata`; ID sequences were checked.
  - `start.bat` skips the local PostgreSQL when `DATABASE_URL` is set. Tests run locally with `USE_LOCAL_DB=1`.
  - Uploaded images still live in `backend/media` on this computer; the database only stores their paths.
- **Concurrency**: stock changes lock the row (`SELECT … FOR UPDATE`) inside a transaction, and order items are locked in sorted id order to avoid deadlocks. DB `CHECK` constraints forbid negative stock and reserved > stock.
- **Arabic search**: tolerant regex for أ/ا/إ/آ, ة/ه, ى/ي and diacritics. A trailing ة/ه is ignored, so «مطرزة» also finds «مطرز».
- **AI**: the separate module `ai_assistant/provider.py` holds the only external connection. Model `claude-opus-5-5` (configurable with `AI_MODEL`) uses structured JSON output and server-side refusal fallback (`fallbacks: "default"`).
  - Only the request text and the public lists of category and city names are sent, plus public offer facts for marketing drafts and aggregated numbers for summaries. No names, phones, addresses or emails are sent.
  - AI output is validated against real categories and cities, and unknown values are dropped. Results always come from database queries. Money is always calculated in Python.
- **Uploads**: JPEG/PNG/WEBP only, verified with Pillow, max 5 MB (configurable), with an image-count limit per offer. In development, Django serves media. In production, serve `/media` as static files from the web server.
- **Admin audit**: API admin actions are written to `AuditLog`. Django admin actions use Django's built-in `LogEntry`.
- **Port selection**: another local project already uses port 8000, so `scripts/launch.ps1` picks the first free API port and passes it to the app (`EXPO_PUBLIC_API_PORT`).
- **Not built (needs a decision or credentials)**: online payment, a real carrier API, email/push notifications, iOS verification.
