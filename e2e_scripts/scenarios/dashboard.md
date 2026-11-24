# Scenario pack: J22 Dashboard widgets and summary tiles (dashboard)

Journey: `dashboard` (J22, P2, layers visual + e2e). Plan: `specs/dashboard.md`. Tests: `tests/journeys/dashboard/`.
Analyst pass 2026-10-09. Sources are the Tech Debt Radar KB (care portal, Jira, support tickets, code index); citations are `file#chunk_id(first 8)`. The KB server disconnected part way through the session, so a few rows are marked UNVERIFIED (seen live only, no KB chunk).

## What the KB says the dashboard is
- After login the user lands on the Dashboard, which shows Net Sales, Net Purchase, Gross Profit, Customers/Patient, Cash in Hand and Due Payments; scrolling shows Fund Summary, Outstanding, Stock and other reports; a Shortcut Keys panel lists keyboard shortcuts; the user picks a predefined date range or a custom one (`careportal_enriched_v5.csv#47746e07`, `careportal_enriched_v5.csv#6bd7001f`).
- Total Sales, Total Purchase, Total Income and Total Expenses; chart of sale and purchase; cash in/out flow; Page Down shows Fund Summary, Outstanding, Business, New Added, Stock and Pending bills; left menu Master, Sale, Purchase, Accounting Transactions, Stock Management, Banking, Reports, CRM, Utilities & Tools (`careportal_enriched_v5.csv#d3e3adba`).
- Only Net Sale, Net Purchase and the flow charts can be customised (`careportal_enriched_v5.csv#fc71fed5`); the configuration screen is `/dash-config` (`codekb:MargBooks:screen#44972385`).
- Component `DashBoardComponent`, routes `/` and `/dashboard` (`codekb:MargBooks:screen#5853f9a5`).
- Header figures come from `usp_MainDashboardHeaderData(@complinkid, @fromdate, @todate, @type)`, which computes total sales/purchases/income/expense for the period and the same figures for a previous period of the same length (`codekb:MargBooks:schema#4c85a3e3`). Cash flow comes from `POST /DashBoard/Dasboard` (`codekb:MargBooks:api#c697966a`). Mobile equivalents: fund summary, outstanding, business, new-added (`codekb:MargBooks:api#e1abf894`, `#c7a3e4e9`, `#5fa32088`).
- Shared date-range component `ReportDateRange` (`codekb:MargBooks:screen#c89a1319`). Report screens default to today with This Month, Yesterday, Last 7 days and Custom (`vimeo_transcripts_hinglish_english.csv#0e5455bc`).
- The Financial Year dropdown is on the dashboard window (`careportal_enriched_v5.csv#9c76fd58`, `#42cc58f4`).

## Known defects and complaints (bugs cluster here, T6)
- MB-024396: dashboard total sale 97000 vs sale analysis 75000, and "the date filter is not working" (`jira_vectordb.csv#4017ad79`, `support_tickets_vectordb.csv#e5ca1bda`).
- "Sale value not match on dashboard" (`jira_vectordb.csv#0bf8d367`); "Dashboard sale not matched with sale register month march" (`jira_vectordb.csv#58aa7aec`).
- 77 tickets on balances: dashboard vs mobile vs ledger mismatch, sale and purchase not shown on the dashboard, opening balance expected in receivable/payable (`support_tickets_vectordb.csv#6c674522`).

## Scenarios
Positive
- DB-01 The dashboard shows the three summary cards Net Sale, Net Purchase, Gross Profit, each with "₹current from ₹previous" and a change percentage (#47746e07, #d3e3adba).
- DB-02 The tile sections Fund Summary, Outstanding, Business, New Added, Stock, Pending are shown with their tiles (#d3e3adba). Tile names (Bank Balance, Cash Balance, Current/Overdue Receivable, ...) UNVERIFIED in KB, seen live.
- DB-03 The period picker offers predefined ranges and a custom range (#47746e07, #c89a1319). Exact option list UNVERIFIED in KB.
- DB-04 Choosing a period relabels the picker and reloads the figures for that period (#4c85a3e3).
- DB-05 The chosen period is remembered after a reload. UNVERIFIED (seen live).
- DB-06 Refresh Dashboard recalculates and moves "Last Sync" to now. UNVERIFIED (seen live: the first paint shows the figures of the last sync).
- DB-07 Net Sale opens the Sale Register, Net Purchase the Purchase Register, Gross Profit the Gross Profit/Loss report (#2 "reports reachable from the Dashboard" `onedrive_processed_data.csv#dcc783a9`).
- DB-08 The Shortcut Keys panel opens from the header and lists HOME/DASHBOARD Alt+H (#47746e07); Alt+H returns to the dashboard from another screen.
- DB-09 An item created today is counted in New Added > Items for Today, and the count drops when it is deleted (#d3e3adba "New Added"). Exact count semantics UNVERIFIED.

Consistency (figures the test cannot own, read at the same moment)
- DB-10 The "from" (previous) figure of each card for This Month equals the current figure for Previous Month (#4c85a3e3 previous period).
- DB-11 Each card's percentage equals (current - previous) / previous x 100 (derived; UNVERIFIED rounding).
- DB-12 Net Sale equals the Sale Register total for the same range (MB-024396, #0bf8d367, #58aa7aec). NEEDS DECISION: Net Sale is net of GST, the register includes it (see spec).

Negative and edge
- DB-13 A custom date typed in the app's dd-mm-yyyy format keeps that date (MB-024396 "date filter is not working").
- DB-14 A custom range whose From is after To is refused. UNVERIFIED expected behaviour.
- DB-15 A custom range outside the books year is refused (min/max attributes 2026-04-01..2027-03-31 seen live). UNVERIFIED.
- DB-16 Clicking a Fund Summary / Outstanding tile drills into the report. UNVERIFIED (KB silent).
- DB-17 Previous period equals 0: percentage shows 0.000%, not a division error (seen live).
- DB-18 A limited-rights user sees only permitted tiles (role rights). Not covered: no limited user on the QA login.
- DB-19 Financial year switch from the dashboard (#9c76fd58). Owned by J-company-switch, not repeated here.
