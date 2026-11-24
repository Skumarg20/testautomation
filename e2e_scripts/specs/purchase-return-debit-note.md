# Plan: J14 purchase return / debit note (purchase-return-debit-note)

Scenario pack: `scenarios/purchase-return-debit-note.md`. Tests: `tests/journeys/returns/test_purchase_return.py`, `tests/journeys/returns/test_debit_note_voucher.py`.
Status: DRAFT for QA/BA review. Observed live on 2026-10-08 with throwaway probes (QA tenant, `garments` login, company "Garments New 29-08 (GANE29)"; the `chemist` login opens the same company).

Existing coverage is not repeated: `tests/journeys/purchase/test_return.py` (PR-001..PR-007, journey `purchase-itc`) and `tests/journeys/accounting/test_debit_note.py` (DN-001..DN-006, journey `payments-ledger`).

## State of the tenant that blocks the older purchase page objects (seen 2026-10-08)
1. Purchase > Bill / Return now open the "Select Party" window by themselves on Create/F2. `PurchaseEntryForm.choose_vendor` clicks the Party Name field first and times out (the open window covers it). `tests/journeys/purchase/test_return.py::...PR-002` fails this way today (run 2026-10-08, `seed_bill` -> `choose_vendor`).
2. The company has no item codes: "Select Item" has columns Description, Packing, Stock, Unit, Sale Rate; there is no `itemcode` column and no item "3". `EntryGrid.select_product` (by code "3") cannot pick a product, so `seed_bill` cannot create the bill a by-bill return needs.
These are test-infrastructure findings, not app defects; they belong to the purchase journey owner. The J14 tests here work around both in their own modules (`pages/returns/party_picker.py`, `pages/returns/manual_return.py`) without changing the shared pages.

3. Shared `Confirmation.answer_yes` looks for a button named "Yes"; the app's confirmation buttons carry aria-label "Close", so their accessible name is "Close" and the click times out (seen in this journey's teardown after an unsaved return form).

## Preconditions
- `page_as("garments")`, dashboard open, company "Garments New 29-08" ensured (the login's company is switched by other suites).
- Returns: each test creates its own item `QA-<run_id>-Return` with opening stock 10 in Main Store (non-batch item), refreshes its balance (a new item is not taken by "Select Item" before that, see `specs/inventory.md` D6), returns 3 at rate 100 to "Cash Account" (manual return), and deletes the return afterwards. The item stays (an item with opening stock cannot be deleted). Group `purchase-stock`.
- Debit notes: Dr "Cash Account" / Cr "Additional Charges On Free Items", 500, today, narration `QA-<run_id> debit note`; deleted afterwards. Group `chemist-tenant` (voucher numbers are company-wide, as in the existing DN tests).

## Screens and locators (verified live)
| Thing | Locator / behaviour |
|---|---|
| Return list | Purchase > Return: heading "Purchase Return debit Note List", opens on "Today". Columns `partyBillNo` (Invoice No.), `billDate` ("08 Oct 2026"), `tmp_LedgerName` (Party), `tmp_stationname`, `totaliteminvoice` (Amount). Its date filter has no "This Week" link (the shared `DocumentList.filter_this_week` clicks an unrelated link there) |
| Return entry | tab "Purchase Return Debit Note 1"; Party Name, Entry Date, Dr. Note (number, e.g. DN00001). Bill-details window: return of bill Single/Manual (`#returnOfBill`). Grid as other purchase documents (`itemLinkID`, `quantity`, `free`, `salePurchaseRate`, `discount1`, `DisplayAmount`) |
| Product | product cell opens "Select Item" (searchbox "Search"; click the row). A non-batch item goes straight to the quantity editor `#txt-quantity-0` |
| Save | End -> focus moves to Bill Value; End again -> window "Mode Of Payment" (Bill Amount, Cash Account, Google Pay, MargPay, Paytm, PhonePe), its SAVE -> success toast. The SAVE is pressed inside that window (the shared `_press_save_in_prompt` looks page-wide and missed it once) |
| Return list actions | row menu = Bootstrap dropdown whose items (Delete, ...) are anchors without href (no link role); delete asks a confirmation whose buttons are `#btnYes`/`#btnNo` (aria-label "Close"). The list address `/purchase/debitnote` redirects to the dashboard when opened directly; after a save/delete the sidebar "Return" entry is not clickable until the dashboard is reloaded. A day with no return shows "No Purchase Return debit Note Created Yet" and no search box |
| Debit Note Voucher List | `/transaction/voucher/debitnote/56` opens it directly (used because the sidebar is half-collapsed after a save). Delete: open the row (double click), Delete key, confirm `#btnYes`, success toast. | Accounting Trans. > Debit Note: columns `entryDate` (dd-mm-yyyy), `voucherNo` (0000011...), `tmp_ledgername` (Party Name = the debit row's ledger), `tmp_instype` (Cash), `tmp_amount` |

## Plans
- RT-A (PRD-01): save a manual return of 3 x 100 -> the return list (searched by Dr. Note number) shows one row, party Cash Account, amount 300 (= sum of the returned line; the line carried no tax on screen: CGST/SGST 0.00%).
- RT-B (PRD-02, own item): stock in Main Store after the return = 10 - 3 = 7 (Item List after "Single Item Refresh").
- RT-C (LNK-03, stock part): delete the return from the list -> stock back to 10.
- RT-D (LNK-01): the Dr. Note number is not found in the Debit Note Voucher List ("DN00001 Not Found!" seen live): a purchase return does not create an accounting debit note voucher.
- RT-E (PRD-11 area, numbering): with a saved return (its Dr. Note number N), start a new return for the same party -> the proposed Dr. Note number must differ from N. Seen live once: a new return proposed DN00001 while DN00001 existed (left by a probe), and its save was refused with "Bill No. Already Exists!" (toast). Pinned by `test_next_return_proposes_a_dr_note_number_not_yet_used`; a failure there is an app defect candidate, not a test fault.
- DN-A (DNV-01, DNV-02): save the voucher, search its number in the list -> one row, date today, party Cash Account, amount 500.
- DN-B (DNV-06): delete the voucher (shared `delete_voucher`) -> its number is no longer listed.

## NEEDS DECISION
- Q12 / LNK-01: RT-D pins the observed behaviour (return is not a debit note voucher). Confirm this is the intended design.
- Tax on the manual return: the item's tax category is "GST Sale - 12%" but the return to Cash Account showed CGST 0.00% / SGST 0.00% and amount 300. Not asserted as a tax rule; needs a decision on the expected GST of a return to an unregistered cash party (PRD-16).
- PRD-02 by bill (partial qty of a bill) and PRD-03/04/05/06 (over-return, free qty, same item twice): need a purchase bill first, which the shared page objects cannot create on this tenant (see above). Blocked until the purchase journey owner updates `seed_bill`.
- PRD-19/DNV-15 print, DNV-03/04 Debit Note Book report, DNV-07 supplier ledger effect, DNV-08 bill adjustment, DNV-09..14 boundaries: not probed yet.
- Cleanup: `QA-<run_id>-Return` items with opening stock stay on the tenant (cannot be deleted).
