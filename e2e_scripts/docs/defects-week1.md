# Week 1 defects

Record a defect here before any test is skipped or `xfail(strict=True)` for it, and only after human agreement.

| ID | Journey | Steps | Expected | Actual | Evidence | Severity | Status |
|---|---|---|---|---|---|---|---|
| D-W1-01 | J05 Purchase and input tax credit | Garments New 29-08, Purchase, supplier "Payable", Sample Item qty 10, rate 100, save line with F10 | Tax Info shows CGST 5.00%/SGST 5.00%, Invoice Value 1,050.000 (the sale side taxes Sample Item at 5%) | Tax Info shows CGST 0.00%/SGST 0.00%, Invoice Value 1,000.000 | Run of 2026-10-07 (test_purchase_itc PU-01); screenshot of the bill after F10 | To be set by product owner | proposed (not agreed; no skip or xfail until agreed; may be an item or purchase tax setting rather than a code defect) |
