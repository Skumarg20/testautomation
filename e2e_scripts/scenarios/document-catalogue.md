# Phase-1 case catalogue (imported from the TypeScript suite)

100 cases, 97 active upstream. Regenerate with `scripts/import_document_cases.py`; data in `test_data/document_cases.json`.

## accounting / contra (6)

| ID | Type | Description | Active |
|---|---|---|---|
| CON-001 | POSITIVE | Create contra with balanced Cr and Dr entries | yes |
| CON-002 | POSITIVE | Create contra and store for future use | yes |
| CON-003 | NEGATIVE | Create contra with zero credit amount | yes |
| CON-004 | NEGATIVE | Create contra without debit account | yes |
| CON-005 | NEGATIVE | Create contra with mismatched credit and debit amounts | yes |
| CON-006 | NEGATIVE | Create contra without account name | yes |

## accounting / credit-note (6)

| ID | Type | Description | Active |
|---|---|---|---|
| CN-001 | POSITIVE | Create credit note with balanced Cr and Dr entries | yes |
| CN-002 | POSITIVE | Create credit note and store for future use | yes |
| CN-003 | NEGATIVE | Create credit note with zero credit amount | yes |
| CN-004 | NEGATIVE | Create credit note without debit account | yes |
| CN-005 | NEGATIVE | Create credit note with mismatched credit and debit amounts | yes |
| CN-006 | NEGATIVE | Create credit note without account name | yes |

## accounting / debit-note (6)

| ID | Type | Description | Active |
|---|---|---|---|
| DN-001 | POSITIVE | Create debit note with balanced Dr and Cr entries | yes |
| DN-002 | POSITIVE | Create debit note and store for future use | yes |
| DN-003 | NEGATIVE | Create debit note with zero debit amount | yes |
| DN-004 | NEGATIVE | Create debit note without credit account | yes |
| DN-005 | NEGATIVE | Create debit note with mismatched debit and credit amounts | yes |
| DN-006 | NEGATIVE | Create debit note without account name | yes |

## accounting / journal (6)

| ID | Type | Description | Active |
|---|---|---|---|
| JN-001 | POSITIVE | Create journal with balanced Cr and Dr entries | yes |
| JN-002 | POSITIVE | Create journal and store for future use | yes |
| JN-003 | NEGATIVE | Create journal with zero credit amount | yes |
| JN-004 | NEGATIVE | Create journal without debit account | yes |
| JN-005 | NEGATIVE | Create journal with mismatched credit and debit amounts | yes |
| JN-006 | NEGATIVE | Create journal without account name | yes |

## accounting / payment (5)

| ID | Type | Description | Active |
|---|---|---|---|
| PM-001 | POSITIVE | Create payment with valid account and amount - delete after | yes |
| PM-002 | POSITIVE | Create payment with short amount - store for reuse | yes |
| PM-003 | NEGATIVE | Create payment without account name - missing account validation | yes |
| PM-004 | NEGATIVE | Create payment with invalid past entry date - date validation | yes |
| PM-005 | NEGATIVE | Create payment with zero amount - amount validation | yes |

## accounting / receipt (5)

| ID | Type | Description | Active |
|---|---|---|---|
| RC-001 | POSITIVE | Create receipt with valid account and amount - delete after | yes |
| RC-002 | POSITIVE | Create receipt with short amount - store for reuse | yes |
| RC-003 | NEGATIVE | Create receipt without account name - missing account validation | yes |
| RC-004 | NEGATIVE | Create receipt with invalid past entry date - date validation | yes |
| RC-005 | NEGATIVE | Create receipt with zero amount - amount validation | yes |

## authentication / login (3)

| ID | Type | Description | Active |
|---|---|---|---|
| TC_001 | Positive | Valid login functionality with valid data | yes |
| TC_002 | Negative | Valid login functionality with invalid data | yes |
| TC_003 | Negative | Valid login functionality with invalid data | yes |

## authentication / register (3)

| ID | Type | Description | Active |
|---|---|---|---|
| TC_001 | Positive | Valid sign-up functionality with valid data | no |
| TC_002 | Negative | Valid sign-up functionality  with invalid data | no |
| TC_003 | Negative | Valid sign-up functionality with invalid data | no |

## purchase / bill (8)

| ID | Type | Description | Active |
|---|---|---|---|
| TC_PM_001 | POSITIVE | Create purchase bill and delete | yes |
| TC_PM_002 | POSITIVE | Create purchase bill from order | yes |
| TC_PM_003 | POSITIVE | Create purchase bill and convert back to challan | yes |
| TC_PM_004 | POSITIVE | Create purchase bill from challan and delete it | yes |
| PB-005 | POSITIVE | Create purchase bill with direct entry and store order | yes |
| PB-006 | NEGATIVE | Create purchase bill without product name | yes |
| PB-007 | NEGATIVE | Create purchase bill with invalid date | yes |
| PB-008 | NEGATIVE | Create purchase bill with 0 qty | yes |

## purchase / challan (6)

| ID | Type | Description | Active |
|---|---|---|---|
| TC_PM_001 | POSITIVE | Create purchase challan and delete the challan | yes |
| TC_PM_002 | POSITIVE | Create purchase challan from order and delete the challan | yes |
| TC_PM_003 | POSITIVE | Create purchase challan with valid data and store challan | yes |
| TC_PM_005 | NEGATIVE | Create purchase challan with past/invalid date | yes |
| TC_PM_006 | NEGATIVE | Create PO without product name | yes |
| TC_PM_007 | NEGATIVE | Create PO with zero quantity | yes |

## purchase / order (7)

| ID | Type | Description | Active |
|---|---|---|---|
| TC_PM_001 | POSITIVE | Create PO and delete | yes |
| TC_PM_002 | POSITIVE | Create PO with direct entry; convert to bill | yes |
| TC_PM_003 | POSITIVE | Create PO with direct entry; close order | yes |
| TC_PM_004 | POSITIVE | Create PO with valid data; store order | yes |
| TC_PM_005 | NEGATIVE | Create PO with past/invalid date | yes |
| TC_PM_006 | NEGATIVE | Create PO without product name | yes |
| TC_PM_007 | NEGATIVE | Create PO with zero quantity | yes |

## purchase / return (7)

| ID | Type | Description | Active |
|---|---|---|---|
| PR-001 | POSITIVE | Verify purchase return with valid data using bill number | yes |
| PR-002 | POSITIVE | Verify purchase return with manual product selection (store return) | yes |
| PR-003 | POSITIVE | Verify purchase return with manual product selection (delete return) | yes |
| PR-004 | NEGATIVE | Verify purchase return without vendor name | yes |
| PR-005 | NEGATIVE | Verify purchase return with invalid date (past financial year) | yes |
| PR-006 | NEGATIVE | Verify purchase return without product details | yes |
| PR-007 | NEGATIVE | Verify purchase return without qty or with 0 qty | yes |

## sales / bill (9)

| ID | Type | Description | Active |
|---|---|---|---|
| TC_SM_001 | Positive | Verify sale bill with valid data and delete bill | yes |
| TC_SM_002 | Positive | Verify sale bill with valid data using order and delete bill | yes |
| TC_SM_003 | Positive | Verify sale bill with valid data using challan and convert back to challan | yes |
| TC_SM_004 | Positive | Verify sale bill with valid data using challan and store bill | yes |
| TC_SM_005 | Negative | Verify sale bill without product details | yes |
| TC_SM_006 | Negative | Verify sale bill with invalid data (future or past) | yes |
| TC_SM_007 | Negative | Verify sale bill without patient and doctor | yes |
| TC_SM_008 | Negative | Verify sale bill without qty or with 0 qty | yes |
| TC_SM_009 | Positive | Verify sale bill with valid data | yes |

## sales / challan (8)

| ID | Type | Description | Active |
|---|---|---|---|
| TC_SM_001 | Positive | Verify sale challan with valid data and delete challan | yes |
| TC_SM_002 | Positive | Verify sale challan with valid data using order and delete challan | yes |
| TC_SM_003 | Positive | Verify sale challan with valid data and convert to bill | yes |
| TC_SM_004 | Positive | Verify sale challan with valid data and store challan | yes |
| TC_SM_005 | Negative | Verify sale challan without product details | yes |
| TC_SM_006 | Negative | Verify sale challan with invalid data (future or past) | yes |
| TC_SM_007 | Negative | Verify sale challan without patient and doctor | yes |
| TC_SM_008 | Negative | Verify sale challan without qty or with 0 qty | yes |

## sales / order (8)

| ID | Type | Description | Active |
|---|---|---|---|
| TC_SM_001 | Positive | Verify sale order with valid data and delete order | yes |
| TC_SM_002 | Positive | Verify sales order with valid data and convert to bill | yes |
| TC_SM_003 | Positive | Verify sales order with valid data and close order | yes |
| TC_SM_004 | Positive | Verify sales order with valid data and store order | yes |
| TC_SM_005 | Negative | Verify sales order without product details | yes |
| TC_SM_006 | Negative | Verify sales order with invalid data (future or past) | yes |
| TC_SM_007 | Negative | Verify sales order without patient and doctor | yes |
| TC_SM_008 | Negative | Verify sales order without qty or with 0 qty | yes |

## sales / return (7)

| ID | Type | Description | Active |
|---|---|---|---|
| TC_SM_001 | Positive | Verify sale return with valid data using bill number | yes |
| TC_SM_002 | Positive | Verify sale return with valid data (manual product selection) | yes |
| TC_SM_003 | Positive | Verify sale return with valid data (manual product selection) | yes |
| TC_SR_004 | Negative | Verify sale return without product details | yes |
| TC_SM_005 | Negative | Verify sale return with invalid date (future or past) | yes |
| TC_SM_006 | Negative | Verify sale return without patient and doctor | yes |
| TC_SR_007 | Negative | Verify sale return without qty or with 0 qty | yes |
