# Edge-case checklist (apply to every journey)

- Boundaries: zero, one, max, negative, very large amounts; decimals and rounding (odd paise)
- GST: every slab, intra- vs inter-state, exempt/nil-rated, reverse charge, invalid or missing GSTIN
- Dates: backdated, future, financial-year boundary, month-end filing cut-offs
- Duplicates: repeated invoice/voucher number, double submit, refresh mid-save
- Roles: each trade account and any limited user, allowed vs denied, direct URL access
- Tenancy: data from company A must never appear in company B
- State: edit after posting, cancel, delete with dependents
- Validation: required fields, max lengths, special characters, unicode
- Output: totals reconcile across invoice, ledger and GST report; export matches screen
