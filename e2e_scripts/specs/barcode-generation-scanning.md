# Spec: Barcode generation / scanning (J27, barcode-generation-scanning)

Status: DRAFT for QA/BA review (planner pass, 2026-10-09). Scenarios: `scenarios/barcode-generation-scanning.md`.
Account: `garments` login, company pinned to `GARMENTS_COMPANY` (Garments New 29-08). Evidence: throwaway probes 1-18
(deleted), outputs kept under `.claude/tmp-p2-brief/runs/barcode-generation-scanning/`.

## What the live app does (observed 2026-10-09)

Control Room > Barcode (read only, probe 7; values on this company):
Pick item from barcode = Yes; Pick batch from barcode = Yes; Pick rate from barcode = Yes; Barcode Management = Yes;
Name Of Barcode = "Barcode"; Barcode Required = Batch wise; Barcode Numbering Style = Automatic; BarCode Generate = No;
BarCode Length = 8; Barcode Duplicate allowed? = Yes; Require Barcode Print in Purchase? = No.

Create Item (Master > Inventory Master > Item, F2):
- "Basic Info" starts with a Barcode textbox `#txtBarcode` (maxlength 45, `texttransform="uppercase"`), then "Print Lable"
  (No / Yes, Yes selected). The field is EMPTY and EDITABLE although numbering is Automatic (see D1).
- Item Setting panel (gear) has "Barcode required?" Master wise / Batch wise (selected) / Multiple / Parameter wise /
  Serial wise / No, and "Item working style" incl. "Barcode Master wise" (tenant-wide, not touched).
- Typed digits are kept; after save, Edit/F3 shows the same barcode (probe 6).
- A second item with the same barcode saves with "Record Saved Successfully" (probe 5/6) because Duplicate allowed = Yes.

Item List: each row has Edit/F3, Delete and an unnamed third button (class `print`, barcode icon). It opens a
"Barcode Printing" dialog (Close, "P Print", "Clear Qty", grid Product / Packing / Barcode / Print Qty). For a new item
without stock the grid is EMPTY (probe 16/17); for the seeded item "Barcdoe" it lists the batch barcode 11110005 with
Design / Color / Size columns: printing works per batch/parameter, not on the master barcode.

Print Barcode (search "print bar" in the top search -> "Print Barcode", route `/report/printbarcode`, heading
"Barcode Printing"): Print Criteria --Select-- / Manual Item Wise / Item Wise / Category Wise / Company Wise / Purchase
Bill Wise; store "Main Store"; buttons "P Print", "F9 Clear", "Clear Qty"; grid Product / Packing / Barcode / Print Qty.
- Print with nothing listed -> toast "Please Select Item First" (probe 13).
- Item Wise opens "Select Item" (search box + Search By Description / Barcode / Any Where / Top Sale). Search By
  Barcode with the new item's barcode lists exactly that item (probe 10/11). Ok with nothing ticked -> toast
  "You Have To Select Atleast One Item." (probe 11/12). Ticking the row and Ok closes the window but the grid stays
  empty for a stock-less item (probe 13).
- Manual Item Wise opens the Item Master picker (has Delete buttons: never press Delete there).

Sale bill (Alt+N, garments): grid columns Barcode / Product / Packing / Qty / Free / Rate / Disc 1.% / Amount, button
"Fast Scanning (Ctrl+B)". Party is a plain textbox (`txtLedgerName<n>`) that opens "Select Party"; after the party the
focus sometimes stops on Store and Enter there opens the first Barcode cell. The suite's
`GarmentsSalePage.open_new_bill` waits for a party searchbox that no longer exists: each Alt+N opens another
"Sale Bill n" tab and it gives up; `sales/test_sales_invoice_gst.py::test_unknown_barcode_raises_an_alert` errors the
same way today (D3). Scanning the barcode of an own item WITH opening stock loads the line (barcode, product, qty
10.000 = default pick, rate 150.000). For a stock-less own item the result differed: "Alert! Barcode Not Available"
in probe 19, the item loaded in run 1 (D5). The seeded batch barcode 11110005 gave "Barcode Not Available"; the seeded
master barcode 11110023 loaded "Barcdoe".

Opening stock (Yes on "add item Opening"): window "Opening" with Item Name, Store Name (Main Store), Opening Qty *;
the batch barcode is not asked. Item List barcode icon then lists the item, its barcode and Print Qty = stock (10).
"P Print" opens the "Print Barcode" format window: Select Format combobox (22 templates, "Garment_Parameter_38_38"
selected), buttons "F Preview", "Esc Close", "P Print". F Preview opened nothing within 30 s (no page, no dialog).
The format window's Print is never pressed.

Duplicate rule: with "Barcode Duplicate allowed?" switched to No (confirmed by reading it back), a second item with an
existing barcode SAVED in probes 22 and 23 and in run 1, and was REFUSED in runs 2 and 3 (D2). Setting restored to
Yes each time (read back in probe 23).

## Tests (generated, `tests/journeys/barcode/`)

| Test | Assert (seen live) | Data left |
|---|---|---|
| `test_item_barcode.py::test_barcode_typed_on_create_is_kept_on_the_item` | Edit/F3 shows the typed barcode | none (deleted) |
| `test_item_barcode.py::test_second_item_with_the_same_barcode_is_refused_when_duplicates_are_not_allowed` | twin not in Item List (derived: KB says creation is prevented); flips Control Room, restores; `xdist_group("chemist-tenant")` | none |
| `test_barcode_scanning.py::test_scanned_barcode_loads_its_item_on_the_bill_line` | line row has the barcode and own product; bill closed unsaved | stocked item |
| `test_barcode_printing.py::test_barcode_icon_lists_the_item_with_its_stock_as_print_quantity` | row product / barcode / Print Qty 10 | stocked item |
| `test_barcode_printing.py::test_print_opens_the_format_window_with_a_preview` | format combobox + enabled F Preview; closed with Esc Close | stocked item |
| `test_barcode_printing.py::test_item_wise_search_by_barcode_finds_only_that_item` | Select Item lists only own item | none |
| `test_barcode_printing.py::test_item_wise_ok_without_ticking_an_item_is_refused` | toast "You Have To Select Atleast One Item." | none |
| `test_barcode_printing.py::test_print_with_no_item_listed_is_refused` | toast "Please Select Item First" | none |

## NEEDS DECISION

- D1 Automatic numbering: Control Room says Numbering Style = Automatic but Create Item shows an empty, editable
  Barcode (KB says it is pre-filled and disabled). Defect, or does Batch wise move generation to the batch? Auto
  generation is not asserted.
- D2 Duplicate rule is intermittent with "Barcode Duplicate allowed?" = No (saved 3 times, refused 2 times). The test
  keeps the refusal assertion and will fail when the app lets the duplicate through. The refusal message was not
  captured; MB-038597 asks for one naming the existing item.
- D3 `pages/sale/garments/garments_sale_page.py::open_new_bill` is broken by the party-field change; this journey uses
  its own opening helper (`pages/barcode/barcode_sale_bill.py`). The sale-bill-creation owner should fix the shared one.
- D4 Items with opening stock cannot be deleted, so three `QA-<run>-Barcode` items (stock 10) stay per run. Agree, or
  provide a cleanup path (e.g. stock adjustment then delete).
- D5 Scanning a stock-less item: "Barcode Not Available" once, loaded once. Which is intended? Not tested.
- D6 F Preview does nothing visible in the browser; is preview desktop-only?
