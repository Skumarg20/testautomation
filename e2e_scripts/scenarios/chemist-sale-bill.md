# Scenario pack: chemist sale bill (contract C8)

Source: the original suite `margbooks-automation-margbooksteam` (test names and flows), re-expressed here.
"Status" says what the Python port does today. Expected results marked QUESTION were never asserted in the
original suite and need an answer from the KB, the API code, or the product owner before they can be tested.

| ID | Scenario | Status |
|---|---|---|
| CR-01 | Master barcode adds the item and quantity | Ported, asserts quantity |
| CR-02 | Batch barcode adds the item in Batch-wise mode | Ported, asserts quantity |
| CR-03 | Batch barcode in Master-wise mode | QUESTION: original swallowed the failure |
| CR-04 | Multiple-barcode setting | QUESTION: skipped in the original |
| CR-05 | Multi-batch item shows the batch window and a batch can be picked | Ported, asserts quantity |
| CR-06 | Near-expiry (NE) batch can be selected | Ported, asserts quantity |
| CR-07 | Expired (EXP) batch shows the "Expired" warning | Ported, asserts the warning |
| CR-08 | Save a bill by barcode / item code / description / mixed | Ported, asserts print preview appears |
| CR-09 | Save a back-dated bill when back billing is on | Ported, asserts print preview |
| CR-10 | Save a future-dated bill when future billing is on | Ported, asserts print preview |
| CR-11 | Future or back date typed while that billing is off | QUESTION: no expectation in the original |
| CR-12 | Zero quantity | QUESTION: no expectation in the original |
| CR-13 | Negative quantity | QUESTION: no expectation in the original |
| GS-01 | Invoice amount, Exclusive and Inclusive GST, with item/volume discounts | QUESTION: formula lived in a helper never committed |
| GS-02 | Invoice amount with bill discount 1 / 2 / both / amount, both GST types | QUESTION: same helper |
| MO-01..05 | Modify saved bill: replace item, quantity, rate, discounts, batch | Ported, asserts the changed row values (GST amounts: see GS-01) |
| LD-01..03 | Ledger master discount 1, 2, both appear on a new bill | Ported, asserts grid discount |
| LD-04..08 | Ledger special discount 1, 2, volume, all appear on a new bill | Ported, asserts grid discount |
| RV-01..08 | Item rate A to H is the billed rate when set as default | Ported, asserts billed rate |
| DB-01 | Database repair completes | Ported, no result assertion in the original |
