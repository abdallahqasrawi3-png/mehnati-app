# Mehnaty: short requirements, data model and API

## Users and what they can do
| Role | Can |
|------|-----|
| Visitor | Browse and search offers, businesses, suppliers and materials; compare; use the smart assistant. |
| Customer (every account) | Profile, private addresses, sales orders (create, track, cancel while pending), review completed orders, notifications, report content. |
| Home-business owner | Business profile and work images; offers (ready / made-to-order / service) with images, stock and movement history; manage incoming orders and delivery terms; shipments; raw-material purchase orders; expenses; financial reports; AI marketing drafts and summaries. |
| Supplier | Supplier profile; materials with units, specs, stock and minimum purchase; manage purchase orders; shipments; supplier reports. |
| Administrator | Accounts (suspend/activate), business/supplier profiles, categories, cities, carriers, abuse reports, platform indicators, audit log. |

## Data model (Django apps → main tables)
```
core:          City 1─* Area · AuditLog · AbuseReport(target_type, target_id)
accounts:      User (email login) 1─* Address(private: city, area, street, building, floor, apartment, landmark, details, optional latitude/longitude pin)
catalog:       Category(kind=offer|material)
               User 1─1 BusinessProfile *─1 Category, City, Area ; 1─* BusinessImage
               BusinessProfile 1─* Offer(type, price, unit_cost, stock, reserved) 1─* OfferImage
suppliers:     User 1─1 SupplierProfile 1─* Material(unit, price, stock, reserved, min_qty) 1─* MaterialImage
orders:        SalesOrder(customer, business, status, delivery snapshot) 1─* SalesOrderItem(price/cost snapshot)
               PurchaseOrder(buyer, business, supplier, status, delivery snapshot) 1─* PurchaseOrderItem
               OrderStatusLog (exactly one of sales/purchase order)
inventory:     InventoryMovement(offer XOR material, kind, qty, stock_after, reserved_after, order)
shipping:      Carrier(integration) · Shipment(1─1 sales XOR purchase order, idempotency_key) 1─* ShipmentEvent
reviews:       Review (1─1 SalesOrder, rating 1-5)
notifications: Notification(user, kind, ref)
reports:       Expense(business, date, category, amount)
```
Key constraints: `reserved ≤ stock` and non-negative stock (DB `CHECK`), one review per order, one shipment per order, unique idempotency key.

## Order, stock and shipping scenarios
1. Customer orders 2 of a ready item: 2 are reserved → the seller accepts → preparing → ready → completed: stock −2, reserved −2, a `sale` movement is recorded.
2. Customer cancels while pending, or the seller rejects/cancels: the reservation is released (`release` movement).
3. Two customers buy the last unit at the same time: one succeeds, the other gets "insufficient stock" (row lock).
4. A delivery order gets a manual shipment (carrier name, tracking). The seller updates its status; the customer is notified and sees the history.
5. Carrier API down: the shipment stays `pending_carrier` with the error. Retry uses the same idempotency key, so no duplicate is created.
6. A business owner buys 5 m of fabric: reserved → supplier accepts/prepares → shipped (stock deducted) → buyer confirms received (counts in both reports; shown separately as a purchase).

## API (all under `/api/`, JSON, JWT `Authorization: Bearer <access>`)
| Area | Endpoints |
|------|-----------|
| Auth | `POST auth/register/`, `POST auth/login/`, `POST auth/refresh/`, `POST auth/logout/`, `GET/PATCH auth/me/`, `POST auth/change-password/` |
| Reference | `GET cities/`, `GET categories/?kind=` (admin can write) |
| Browse | `GET offers/?q&category&city&area&min_price&max_price&min_rating&max_prep_days&offer_type&available&delivery&ordering`, `GET offers/{id}/`, `GET offers/compare/?ids=`, `GET businesses/`, `GET businesses/{id}/`, `GET suppliers/`, `GET materials/?q&category&city&unit&max_price&min_available&max_delivery_days&delivery&ordering`, `GET materials/compare/?ids=` |
| Owner | `GET/POST/PATCH my/business/`, `POST my/business/logo/`, `POST/DELETE my/business/images/`, `my/offers/` CRUD + `{id}/images/`, `{id}/stock/`, `{id}/movements/` |
| Supplier | `GET/POST/PATCH my/supplier/`, `my/materials/` CRUD + images/stock/movements |
| Orders | `sales-orders/` (list `?role=customer|business&status=`, create, detail, `{id}/transition/`, `{id}/delivery/`), `purchase-orders/` (same, `?role=buyer|supplier`) |
| Shipping | `GET carriers/`, `shipments/` (list, create, detail, `{id}/update_status/`, `{id}/retry/`) |
| Other | `reviews/`, `notifications/` (+`unread_count`, `{id}/read/`, `read_all`), `addresses/`, `expenses/`, `abuse-reports/`, `inventory/low-stock/` |
| Reports | `GET reports/business/?period=day|week|month` (or `from`&`to`), `GET reports/supplier/`, `GET reports/admin/` |
| AI | `GET ai/status/`, `POST ai/search/ {text, target}`, `POST ai/marketing-draft/ {offer_id, extra_facts}`, `GET ai/business-summary/` |
| Admin | `admin/users/` (+`{id}/set_active/`), `admin/abuse-reports/` (+`{id}/resolve/`), `admin/profiles/profiles/`, `POST admin/profiles/{business|supplier}/{id}/` |
