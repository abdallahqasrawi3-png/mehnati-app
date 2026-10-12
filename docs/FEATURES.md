# Feature checklist

Legend: ✅ built and verified · 🟡 built, not fully verified (reason given) · ⛔ not built: needs an outside account, key or decision

"Tests" = automated backend tests (`python manage.py test`, 68 tests, all passing on 2026-10-12).
"Web UI" = clicked through in a browser (Expo web, RTL) on 2026-10-12.

## Accounts and permissions
- ✅ Register / login / logout / change password (hashed passwords, JWT, refresh rotation). Tests + web UI
- ✅ One account can hold customer + business + supplier roles. Tests
- ✅ Private addresses; order privacy; a stranger gets 404 on another user's orders, addresses, shipments, expenses and reports. Tests
- ✅ Specific addresses (street, building, floor, apartment, landmark) with an optional map pin (current location or a pasted Google Maps link); edit saved addresses; the pin is copied into delivery orders and shown to the seller/supplier as a map link. Tests (backend + coordinate parser)
- 🟡 "Use my current location" on a phone: not tried on a real device in this session. It needs location permission and GPS. In the browser it works only on `localhost` or HTTPS.
- ✅ Admin-only endpoints; suspend/activate accounts and profiles; audit log. Tests + web UI (dashboard)

## Catalog, search, comparison
- ✅ Business profile with consent-gated contact details, city/area-only public location, work images, logo. Tests
- ✅ Offers: ready / made-to-order / service, images (type and size validated), soft delete, private unit cost. Tests
- ✅ Categories editable by admins (Django admin + API). Tests
- ✅ Search: keywords (Arabic-variant tolerant), category, city, area, price, rating, availability, prep time, type, delivery, ordering. Tests + web UI
- ✅ Offer comparison and material comparison with unit warnings. Tests + web UI (phone width)
- ✅ Suppliers and raw materials: units, specs, minimum purchase, delivery cost/time. Tests

## Orders and stock
- ✅ Sales orders: one business per order, price/cost snapshots, pickup/delivery, service preferred date. Tests + web UI (create → accept)
- ✅ Allowed transitions per role; customer cancels only while pending. Tests + web UI (actions shown per role)
- ✅ Purchase orders: one supplier, minimum quantity, supplier flow, buyer confirms receipt. Tests
- ✅ Atomic stock reservation; concurrent last-unit test; no negative stock (DB constraints); release on cancel/reject; sale on completion. Tests
- ✅ Inventory movement history and low-stock alerts (notification + list). Tests
- ✅ Delivery terms: fee, payer, estimated/final. Tests

## Delivery
- ✅ Manual shipments linked to the correct order; sender-only updates; recipient view; event history. Tests
- ✅ No duplicate shipments on retry; carrier failure handled (`pending_carrier` + retry). Tests (simulator, test-only)
- ⛔ Real carrier API: no company or credentials supplied. Add an adapter in `backend/shipping/carriers.py`.

## Reviews, notifications, moderation
- ✅ One review per completed order; owners cannot edit or delete; reports of abusive content; admin hides content → rating recalculated. Tests
- ✅ In-app notifications (new order, status change, low stock, shipment, review); a failure never breaks an order. Tests + web UI (badge)
- ⛔ Email / push notifications: later phase.

## Reports
- ✅ Business report: revenue, COGS, expenses, business-paid delivery, estimated profit, incomplete-cost label, best sellers, daily revenue, purchases shown separately. Tests + web UI
- ✅ Supplier report kept separate; admin indicators. Tests + web UI (admin)
- ✅ Expenses CRUD (private). Tests

## AI assistant
- ✅ Natural-language Arabic search with mandatory vs preferred criteria, reasons, and labelled near-matches, all from real records. Tests + web UI
- ✅ Works without a key (built-in rule parser) and during outages (fallback). Tests
- ✅ AI output validated against real categories/cities. Tests (mocked provider)
- ✅ Marketing draft from real facts, never auto-published; business summary with numbers calculated in code. Tests
- 🟡 Live Claude calls: the code is written and handled, but not run against the real API because no `ANTHROPIC_API_KEY` was supplied.

## Platforms
- ✅ Web (react-native-web), Arabic RTL, desktop and phone widths. Web UI
- 🟡 Android via Expo Go: same code. Not verified on a device in this session (no phone/emulator attached). See README to test.
- ⛔ Online payment: intentionally not built (needs a requirement and a gateway).
- ⛔ iOS: not requested and not verified.

## External accounts / keys still needed
| Item | Needed for |
|------|-----------|
| `ANTHROPIC_API_KEY` (Anthropic console) | Claude-powered assistant (optional; rules work without it) |
| Delivery company API docs + credentials | Automatic shipment creation/tracking |
| Production server, domain, HTTPS certificate | Public deployment |
| Expo / EAS account (optional) | Building an installable Android APK/AAB |
