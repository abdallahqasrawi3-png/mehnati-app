
## Your task

Act as a software engineer, user-experience designer and database designer. Build Mehnaty as a working application, with real saved data, protected permissions and tested features. Work in stages and keep explanations short and simple.

Treat this as a fresh implementation based on the documents. Do not use an existing application's behavior to define requirements.

## Confirmed technology

- Backend: Python and Django.
- Frontend: cross-platform React Native, with an Arabic interface and right-to-left layouts.
- API: Django REST Framework to connect React Native to Django.
- Database: PostgreSQL, using Django ORM and migrations.
- Keep permissions, stock updates, order rules and financial calculations on the server.
- Use environment variables for secrets and provide `.env.example` without real credentials.
- Check compatibility before installing packages. Select supported stable versions and lock dependencies.

The owner's React Native instruction replaces the document's Django-template, HTML and Bootstrap frontend requirement. Ask which platforms must be delivered: Android, iOS and/or browser. Confirm where the admin interface should run.

## Purpose and document conflict

Mehnaty helps customers find home-made products and home services. It helps home-business owners present their work, reach customers and manage their activity.

`ar_problem.docx` describes profiles, discovery, comparison, reviews, contact and AI. It suggests delivery and full booking may be postponed. `تطبيق مهنتي.docx` adds suppliers, raw materials, orders, stock, delivery and reports.

**Ask the owner which first-release scope applies before implementing those additional modules.** Keep the requirements below available for the full scope. Omit modules the owner excludes.

## Questions before the affected work

Ask before choosing business rules. Record answers in `docs/DECISIONS.md`. Continue work that does not depend on a missing answer.

1. Is the first release the smaller discovery scope or the full scope with suppliers, orders, stock, delivery and reports?
2. Which target platforms and admin interface are required?
3. Which accounts need approval? May one account also be both a supplier and a home-business owner? The document explicitly allows customer and business-owner roles together.
4. What are the exact order transitions, cancellation rules and completion responsibilities? How do made-to-order products and services handle prices, appointments and availability?
5. Which currency and initial locations apply? How should customers contact providers? Who pays delivery, and is its cost estimated or final?
6. What does a review rate, and how many reviews are allowed per completed order? If orders are excluded, what permits a customer to review?
7. Which delivery and AI providers are available? What credentials and API documentation can the owner supply?

Do not invent approval rules, fees, commissions, payment methods, refund rules, service-booking rules or review limits. The sample price in shekels is not confirmation of the application currency.

## Roles and access

| Role | Document requirements |
| --- | --- |
| Visitor | Browse products, services and applicable raw materials; search without signing in. |
| Customer | Manage a profile, compare offers and, when orders are included, place and track orders, cancel under agreed rules and review completed experiences. |
| Home-business owner | Manage a business profile, products, services and images. In the full scope, manage own orders, stock, purchases, costs and reports. |
| Supplier | In the full scope, manage a supplier profile, raw materials, prices, units, quantities, minimum purchases, orders and own reports. |
| Delivery company | In the full scope, connect through an available API or use manually recorded shipment details. An interactive carrier account is not required by the document for the first release. |
| Administrator | Manage accounts, categories, content, reports of abuse, account reviews and platform indicators. |

Check permissions and record ownership on every protected server operation. Users may access only authorized orders, addresses, reports and other private information.

## Functional requirements

### Profiles and offers

Business profiles include name, description, activity category, city/area, consented public contact details, hours, collection/delivery options, account status, genuine ratings and work images.

Show only the general location publicly by default. Protect exact home and delivery addresses.

Owners can add, edit and delete offers with title, description, images, price, category, preparation time and availability. Distinguish ready-stock products, made-to-order products and services. Ask how deletion should affect existing orders. Categories are editable through administration.

For the full scope, supplier offers also include specifications, unit, available quantity and minimum purchase. Display units clearly when comparing prices.

### Search and comparison

Build ordinary search first. Support keywords, category, city/area, price, rating, availability, preparation time and offer type. Compare actual offers with clear prices and units. Supplier comparison also includes specifications, minimum quantity and delivery cost/time when available.

### Orders and inventory for the full scope

Keep sales orders separate from raw-material purchase orders. The detailed document requires one home business per sales order and one supplier per purchase order in the first release.

Do not add online payment initially. Its introduction requires an explicit requirement and a suitable gateway. Do not infer a different payment method from its absence.

Save prices, quantities and important order details when the order is created. Save cost information when available so later edits do not change historical records.

The document suggests sales states such as awaiting acceptance, accepted, preparing, ready, in transit, completed, rejected, cancelled and delivery failed. Purchase examples include awaiting acceptance, accepted, preparing, shipped, received, rejected and cancelled. These are examples: confirm the exact transitions and permissions before coding them.

Reserve limited stock atomically when creating an order. Prevent negative quantities and conflicting reservations. Release reserved quantities after an allowed rejection or cancellation. Record inventory movements and allow owners/suppliers to set low-stock alert thresholds. Apply stock rules only to relevant offer types.

### Delivery for the full scope

Support supplier-to-business and business-to-customer shipments. Store the linked order, sender, recipient, carrier, tracking number, status, last update, and cost/estimated arrival when available.

Manual shipment entry must work without an external API. Keep carrier integrations separate and support only documented capabilities. Prevent duplicate shipment creation during retries. Claim external creation only after carrier confirmation. Protect addresses and phone numbers.

### Reviews and notifications

For the full scope, allow customer reviews after completed orders and link them to orders where possible. Prevent disallowed duplicates according to the owner's answer. Business owners cannot directly edit or delete customer reviews. Provide reporting of abusive content.

Start with in-app notifications for new orders, status changes, low stock and important shipment updates. A failed notification must not lose an order. Email and push notifications can follow later.

### Reports for the full scope

Show completed sales, completed orders, best-selling products, recorded product costs, direct expenses and estimated operating profit by day, week or month. Suppliers see their own purchase/sales reports. Keep supplier and home-business figures separate.

Estimated operating profit = completed-order revenue - cost of sold products/services - recorded direct expenses.

Include recorded packaging, delivery paid by the business, applicable commissions and other direct costs. This formula does not authorize introducing a platform commission. Label results when costs are incomplete. Show raw-material purchases separately; do not deduct all purchases as consumed materials automatically.

### AI assistance

Add AI after ordinary workflows work. Convert Arabic requests into search criteria and query real database records. Separate mandatory conditions from preferences. Explain recommendations and clearly label any near matches and unmet conditions.

Generate marketing drafts only from supplied facts and require owner review before publishing. Summarize real sales, orders and stock where those modules are included. Calculate money in application code.

Use a separate AI integration component. Keep its key on the server. Core functions must work without a key or during an outage. Do not invent offers, prices, quantities, ratings or delivery dates. Limit sensitive data sent to external services.

## Screens and security

Provide home, categories, search results, offer details, business profiles, registration, login and role-appropriate dashboards. For the full scope, add sales orders, stock, reports, supplier listings, raw-material details, purchase orders, shipments and administration.

Use clear Arabic, readable layouts and consistent navigation. Include loading, empty, success and error states. Every enabled action must work and save the correct data.

Use Django password protection, server-side validation, safe image type/size checks, secure authentication for React Native, HTTPS in production, protected secrets, administrative audit records and restorable backups. Keep sensitive details out of errors and logs.

## Short implementation plan

| Stage | Deliverable |
| --- | --- |
| 1 | Resolve scope questions; write short requirements, database relationships and API contracts. |
| 2 | Set up Django, PostgreSQL, React Native, authentication and permissions. |
| 3 | Build profiles, categories, offers, images, search and comparison; suppliers if included. |
| 4 | Build approved sales/purchase workflows, stock reservations and inventory history if included. |
| 5 | Add applicable delivery, reviews, notifications and financial reports. |
| 6 | Add AI, test complete journeys, fix issues and document operation. |

Organize Django by responsibility, such as accounts, catalog, suppliers, orders, inventory, shipping, reviews, reports and AI. Add only modules needed for the agreed scope.

## Testing and completion

Run meaningful tests after each stage. Cover registration/login, role and ownership checks, offer creation, search and filtering. For selected modules, also cover sales/purchase orders, allowed state changes, concurrent stock reservation, cancellation release, shipment ownership, completed-order reviews, financial calculations, missing AI credentials and carrier failures.

Verify Arabic RTL on every agreed platform. Fix failures before proceeding. State clearly when a test could not run. A feature is complete only when it works, saves correct data, enforces permissions and passes its checks.

Deliver source code, locked dependencies, environment examples, database migrations, automated tests, optional clearly marked demo data, a simple README, `docs/DECISIONS.md`, and a feature checklist. The README must explain setup, database configuration, app/backend startup, administrator creation and test commands. List external accounts or keys still needed.

After each stage, briefly report what was implemented, actual test results, remaining issues and the next step.
