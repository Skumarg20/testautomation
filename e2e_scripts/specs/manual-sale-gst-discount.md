# Plan: manual cases AJ-013..AJ-018, AJ-092, AJ-093 (pilot batch)

Status: VERIFIED LIVE 2026-10-06 on company "Garments New 29-08 (GANE29)", party Ajay (intra-state), item Sample Item (5%, rate 100, qty 3, gross 300.000). Nothing saved. Source: `scenarios/manual-sale-purchase.md`. Tests: `tests/journeys/sales/test_sales_gst_discount.py`. Journey `gst-calculation` set to `generated`.

## Earlier block, resolved
The blocked run saw company "tEST-1" and a chemist-style grid with a "Select Series" dialog. A fresh login lands on GANE29 with the garments grid (Barcode, Product, Packing, Qty, Free, Rate, Disc 1.%, Amount) and no series dialog. Cause: a stale `.auth/` session; deleting it fixed it. `fixtures/session.py` (base_url merged into context options) reviewed and kept.

## Locators (verified live; no test ids exist, ids carry a window number so formcontrolname is used)
| Thing | Locator |
|---|---|
| Item discount 1 cell | grid cell `[col-id="discount1"]`, click then the input `#txt-discount1-<row>` takes focus; text must be inserted (`keyboard.insert_text`), typing key by key is ignored; Enter commits |
| Bill discount 1 / 2 / amount | `[formcontrolname="billDiscountInPercent"]`, `billDiscountInPercent2`, `billDiscountInAmount`; click, Ctrl+A, `keyboard.type`, Tab. Fields exist only while the switches are on |
| Calculation type | `#aControlRoomSetting` then `#calculationTypeForSale` (1 Inclusive, 2 Exclusive, 3 Tax on MRP(inc.)); original here: Exclusive |
| Bill discount switches | `#aControlRoomSetting`, `#sale-bill-discount` (Configure), checkboxes `#billDiscountSale`, `#billdiscount2Sale`, `#saleBillDiscountInAmount`, `#btn-Save`; originals here: all off (Item Discount on) |

## Cases
| Case | Setup | Expected (derived, Decimal) | Live | Result |
|---|---|---|---|---|
| AJ-013 | Exclusive, item disc 1 = 10% | taxable 270, CGST=SGST 6.750, invoice 283.500 | agrees | generated, passed |
| AJ-014 | Inclusive, no discount | invoice 300.000, tax 300*5/105 = 14.286, CGST=SGST 7.143 | agrees | generated, passed |
| AJ-015 | Exclusive | CGST=SGST 7.500, invoice 315.000 | agrees | generated, passed |
| AJ-016 | bill disc 1 = 10% | taxable 270, tax 6.750 each, invoice 283.500 | agrees | generated, passed |
| AJ-017 | bill disc 2 = 10% | same as AJ-016 | agrees | generated, passed |
| AJ-018 | bill discount amount 45 | taxable 255, tax 6.375 each, invoice 267.750 | agrees | generated, passed |
| AJ-092 / AJ-093 | existing SI-01..SI-04 | see `sale-invoice-gst.md` | | passed |

## Product-owner decisions (2026-10-06) and live findings
- Bill discounts 1 and 2 compound (discount 1 first, then discount 2 on the reduced total). Verified live: 10% then 10% on 300 gives taxable 243, tax 6.075 each, invoice 255.150 (bill discount amount field shows 57); 20% then 10% gives 216 and invoice 226.800. Additive would give 220.500, so the app compounds as decided. Test: `test_aj016_017_bill_discounts_1_and_2_compound`.
- Invoice round-off to the nearest whole rupee (.67 up, .37 down, exactly .50 assumed up, unconfirmed). Live: the sale bill screen does NOT round. Invoice Value shows 267.750 (45 off) and 255.150 unrounded; the 47-off, 51-off and exact .50 (50 off) figures are not yet observed live. The only round-off on the screen is a manual "Round Off" ledger row (Additional Details grid, blank row, Space, search "Round Off"); adding it gives 0.000 and does not change the invoice. The ledger exists (balance 0.320 Dr), so the app posts round-off somewhere, probably when a bill is saved. Not verifiable without saving a bill (open question Q1). Tests `test_invoice_value_is_rounded_to_the_nearest_rupee` (265.650 -> 266, 261.450 -> 261) assert the rule against the on-screen Invoice Value and fail: reported as an APP DEFECT (decided by the user 2026-10-14: the on-screen Invoice Value must round to the rupee; still 265.650 and 261.450 on V 4.3.599.b). Exact .50 not asserted.
- The grid "Amount" column stays gross after an item discount because of Sale Bill Setting > Advance Setting > "Amount Calculation On Billing" (Rate * Quantity | Rate * Quantity - Discount | Net Amount); current value gives gross. Not a defect; tests assert tax and invoice only.

## Still NEEDS DECISION
- Masked discount inputs: Ctrl+A does not select, so typing appends to the old text ("10" typed after "0" gives "100"); tests clear with `fill("")` first. Intended?
- Inclusive combined with a discount (observed invoice 270.000, tax 6.429 each) is not asserted yet.
- Rounding of tax (D5): chosen figures avoid half ties at 3 decimals.
