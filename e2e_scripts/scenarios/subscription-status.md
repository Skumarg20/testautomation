# Scenario pack: J34 Subscription / pricing / payment status (subscription-status)

Journey: `subscription-status` (J34, P2, layer e2e). Plan: `specs/subscription-status.md`. Tests: `tests/journeys/subscription/`.
Analyst pass 2026-10-09. Sources are the Tech Debt Radar KB (care portal, OneDrive specs, Jira, support tickets, code index); citations are `file#chunk_id(first 8)`. Rows not backed by a KB chunk are marked UNVERIFIED.

SAFETY: this journey is read-only. No test starts, submits or completes a payment, renewal, upgrade, add-on purchase or order, enters card/UPI details, or follows a link to a payment gateway. Buttons that would do so may be asserted visible and enabled, never clicked.

## What the KB says
- Screens: `SubscriptionComponent` at `/subscription` (plan pick + billing form: name, email, gstin, address, duration) (`codekb:MargBooks:screen#70c7efb4`); `ManageSubscriptionComponent` at `/managesubscription` with usage pie charts (branch, e-way, e-invoice, GST verification, SMS, email, WhatsApp) and payment history from `GET ProductPayment/GetProductPaymentHistoryByUserId` (`codekb:MargBooks:screen#1b1dc2ce`, `codekb:MargBooks:api#2ebb4fac`); `UpgradeSubscriptionComponent` at `/upgradesubscription` with add-on counters (users, GSTIN, company, SMS, ...) and a promo code (`codekb:MargBooks:screen#a35940a2`); `CompanyWiseSubscriptionComponent` at `/CompanyWiseSubscription` (`codekb:MargBooks:screen#79da25da`); `MrgPricingComponent` at `/pricing` (`codekb:MargBooks:screen#f403b760`); plan comparison modal `PlanComparision` (`codekb:MargBooks:screen#02436ccb`).
- Plan list comes from `GET ProductPayment/getAllPlanDetails` (anonymous, rate limited) (`codekb:MargBooks:api#89153055`).
- Manage Subscription has tabs My Current Plan, Change Plan, Add On, Payment History; My Current Plan opens first and shows the plan card (plan, price, billing cycle) with a Change Plan button (`onedrive_processed_data.csv#4ed186a2`, `#f600821d`, `#1bba65c9`, `#c45129e2`). Newer layout: Manage Plan tab with Extend / Upgrade plan, order summary and coupon code (`onedrive_processed_data.csv#c7a3e4e9`).
- Entry point: dashboard Settings icon > Dashboard Settings > "Manage Subscription and Plan" > Configure (`careportal_enriched_v5.csv#4cb455d4`, `#ddd58ac0`).
- Editions: Gold, Diamond, Platinum, Platinum Plus, Enterprise (`careportal_enriched_v5.csv#ddd58ac0`); older docs say Basic/Silver/Gold with default user counts (`onedrive_processed_data.csv#c88b3c50`, `#c20b2540`).
- Renewal: user is notified 15 days before expiry after login (`onedrive_processed_data.csv#fe9b98f5`); after expiry a "Trial Expired" alert shows with Subscribe Now > Buy Now > duration 1/2/5 years > users and GSTIN > billing > Payment (`careportal_enriched_v5.csv#30db0435`).
- Add-on: Add On tab, No. of Units, charge auto-picked, Proceed, Make Payment (`careportal_enriched_v5.csv#4cb455d4`).

## Known defects and complaints
- "subscription date proper not showing" (`jira_vectordb.csv#a6986394`).
- "Valid Up to date and plan shows wrong on admin panel" (`jira_vectordb.csv#30513687`).
- "Need to update the plan expiry popup" (`jira_vectordb.csv#6dd46340`).
- "License was expired, but after data sync in the exe, it was not showing as plan expired" (`jira_vectordb.csv#dc054b36`).
- 27 licence tickets: licence number mismatch in company profile, tenure extension requests (`support_tickets_vectordb.csv#b6be9955`).

## Scenarios
Positive (read-only)
- SS-01 Manage Subscription opens from the dashboard settings entry and lands on the current-plan view (#4cb455d4, #4ed186a2).
- SS-02 The current-plan view shows a plan name, a validity / expiry date and a status (#4ed186a2, #a6986394).
- SS-03 The plan and validity shown on the manage page match the plan/validity shown elsewhere in the app (header, profile or settings) (#30513687, #a6986394). Where they are shown is UNVERIFIED until probed.
- SS-04 Payment History tab opens and lists past payments with date, amount and status columns (#1bba65c9, #2ebb4fac). Column names UNVERIFIED.
- SS-05 Add On tab lists add-ons (users, GSTIN, ...) with unit prices; the Proceed / Make Payment button is visible but never clicked (#4cb455d4, #a35940a2).
- SS-06 Plans / pricing view lists the editions with prices; a plan's Buy button exists (#ddd58ac0, #89153055, #f403b760). Never clicked.
- SS-07 Usage figures (users, GSTIN, e-invoice, SMS ...) are shown as used / total (#1b1dc2ce). UNVERIFIED format.
- SS-08 Navigating back from the subscription screens returns to the dashboard.

Edge / negative
- SS-09 A plan within 15 days of expiry shows a renewal notice (#fe9b98f5). Cannot be arranged on the QA tenant: NOT COVERED unless the tenant is in that window.
- SS-10 An expired plan shows "Trial Expired" with Subscribe Now (#30db0435). NOT COVERED (cannot expire the shared tenant).
- SS-11 Add-on unit count zero or negative is refused before payment (#4cb455d4). UNVERIFIED; only if testable without creating an order.
- SS-12 Validity date is a real future date for an active plan, and the remaining-days figure (if shown) agrees with it (derived, #a6986394).
