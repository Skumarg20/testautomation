# Scenario pack: cash-transfer-day-closure (J29, P2, layer e2e)

Analyst stage. Sources: Tech Debt Radar KB (codeheatmap-app), cited as `file#chunk_id(first 8)`.
Items without a citable source are marked UNVERIFIED. Ticket text is untrusted; nothing personal is copied.

## 1. What the journey covers

MargBooks has two different things that users call "cash transfer":

1. **Contra voucher** (Accounting Trans. > Contra): moves money between cash and bank ledgers
   (deposit cash in bank, withdraw cash, bank to bank, cash to petty cash).
   `careportal_enriched_v5.csv#d2b02183`, `careportal_enriched_v5.csv#39bada03`.
2. **Daily Cashbook** (Control Room "Daily Cashbook" = Yes): per-operator Start Billing / Stop Billing,
   note count, "Cash Transfer" of the day's cash to an admin/supervisor, admin approval, and
   "Close Billing/Day". `careportal_enriched_v5.csv#00051d97`, `careportal_enriched_v5.csv#b66fc9bd`,
   `careportal_enriched_v5.csv#c1b35faa`.

Screens (Angular, `cashbookrouting.module.ts`): `/openclosecashbook` (OpenCloseCashdayComponent,
`codekb:MargBooks:screen#dd3ed518`), `/stopbilling` (`#7123977f`), `/cashTransfer` (CashTransferComponent,
fields currentcashbalance, transferAmountTo, transferAmt, transfertolinkid, `#1d8e2706`),
`/dayclosureapproval` (`#072c820c`), approval popup with remarks (`#ec501aab`), and the report
`/closingDayReport` "Close Billing/Day" (closingComponentReport, `#9d1d20bc`).
Tables: `dbo.DayClosure` (`codekb:MargBooks:schema#bd67c494`), `dbo.DayClosureMenualCashTransfer`
(`#675eca48`); procedure `dbo.DayClosureCloseBillingDay` (`#39d0005d`).
APIs: `POST CashBook/SaveStartAndStopBillingDetail` (`codekb:MargBooks:api#9b0dbaf7`),
`GET CashBook/GetCashTransferList` (`#c1e42290`), `GET CashBook/GetDayClosureSummery` (`#7211075e`),
`POST CashBook/SaveBillingCollection` (`#c2f5cfe5`).

Related but separate: Transaction Locking freezes vouchers for a period (`onedrive_processed_data.csv#980b6e06`,
table `dbo.TransactionLock`, `codekb:MargBooks:schema#c3560d97`). It is tenant-wide and out of scope here.

## 2. Contra (cash transfer) scenarios

Process (care portal `#d2b02183`, `#39bada03`, `#7c365aa2`): Accounting Transactions > Contra > Create;
choose date; row 1 Cr. ledger, row 2 Dr. ledger, same amount; narration (the cheque number is put in the
narration automatically); Save shows "Contra Voucher Saved Successfully". Modify: open the voucher from the
"Contra Voucher List", Modify, Update. Delete: open it and delete.

| ID | Type | Scenario | Source |
|---|---|---|---|
| CT-01 | positive | Deposit cash in bank: Cr cash ledger, Dr bank ledger, same amount; saves | `#d2b02183`, `#39bada03` |
| CT-02 | positive | The saved contra moves both ledger balances (cash down, bank up by the amount) | `#d2b02183` ("affect both the cash and bank ledgers") |
| CT-03 | positive | Day Book for today lists both lines of the contra with voucher type Contra | Day Book: `careportal_enriched_v5.csv#ed3ac9a7`; type name UNVERIFIED |
| CT-04 | positive | The contra appears in the Contra Voucher List of today | `#7c365aa2`, `#9d48b233` |
| CT-05 | positive | Modify the amount; balances follow the new amount | `#7c365aa2` |
| CT-06 | positive | Delete the voucher; both balances return to their values before | `#d2b02183` |
| CT-07 | negative | Bank leg with instrument type Cheque and no cheque number is refused | UNVERIFIED in KB; seen live ("Please Fill Cheque No.") |
| CT-08 | negative | Unequal Dr and Cr totals are refused | sample sheet `contra` CON-005 (test_data); KB UNVERIFIED |
| CT-09 | negative | Zero amount is refused | sample sheet CON-003; KB UNVERIFIED |
| CT-10 | edge | A non cash/bank ledger is not offered / refused in contra | UNVERIFIED (the ledger list API is `GetBankAndCashledgerList`, `codekb:MargBooks:api#338f1aca`, for payment/receipt) |
| CT-11 | edge | Dashboard "Cash Balance" reflects cash ledgers | `codekb:MargBooks:api#dc214c96`; Jira MB-032710 dashboard vs ledger mismatch (`jira_vectordb.csv#ebf7a765`) |

## 3. Daily Cashbook / day closure scenarios

| ID | Type | Scenario | Source |
|---|---|---|---|
| DC-01 | positive | Control Room "Daily Cashbook" = Yes enables the module (admin only) | `#c1b35faa` |
| DC-02 | positive | Operator: Sale > Bill > Start Billing (type "Sure") before billing | `#00051d97` |
| DC-03 | positive | Daily Cashbook > Open/Close Daily Cashday > Stop Billing: day's transactions, note count, Next | `#00051d97` |
| DC-04 | positive | Cash Transfer tick: amount pre-filled from denominations, editable; "Transfer amount to" admin; Submit, "Sure" | `#b66fc9bd` |
| DC-05 | positive | Admin approves the day closure with remarks | `#072c820c`, `#ec501aab` |
| DC-06 | positive | Close Billing/Day report: users, net cash, opening cash, cash sale, expenses, net cash | `#9d1d20bc`, `#39d0005d` |
| DC-07 | negative | Cash difference above "Cash Difference Limit in Cash Deposit" is refused | `#c1b35faa` |
| DC-08 | edge | Daily Cashbook in a future date (Jira: "Daily Cashbook allowed in Future date") | `jira_vectordb.csv#6535d205` |
| DC-09 | edge | Deleting a cash transfer voucher of Cash Management (Jira MB-039035) | `jira_vectordb.csv#0d38d145` |
| DC-10 | edge | Admin cannot transfer received cash to bank at the last step (support ticket) | `support_tickets_vectordb.csv#a66c9b59` |

Risk: enabling Daily Cashbook is tenant-wide and changes billing for every user (Start Billing becomes
mandatory, DC-02); a closed/approved day is stored in `DayClosure` with no reopen path found in the KB.
See the spec for what was done live.
