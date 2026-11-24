# Manual test case pack: sale and purchase (from the QA Excel files)

Generated from `sale and purchase check list.xlsx`, `Sale Bill Module Test Cases Ajay.xlsx` and `test cases stock related (sale module).xlsx`.
Exact duplicates across the files are dropped. Group and Needs are keyword guesses for planning, a human confirms them.
IDs: AJ = Ajay sheet, ST = stock sheet, SC = sale checklist, PC = purchase checklist (number = source row or S.No).

Total unique cases: **329**

## By group

| Group | Cases |
|---|---|
| Stock effect | 66 |
| Discount and scheme | 44 |
| GST and tax | 35 |
| Bill lifecycle (create, modify, delete) | 30 |
| Settings toggles | 29 |
| Batch and expiry | 27 |
| General | 23 |
| External send/print (WhatsApp, email, SMS, print) | 18 |
| Payment (MOP) | 17 |
| Keyboard and navigation | 13 |
| Patient/doctor (chemist) | 9 |
| Multi store and unit | 7 |
| Permissions and users | 6 |
| Additional charges | 5 |

## By what a run needs

| Needs | Cases |
|---|---|
| any trade | 192 |
| changes tenant settings, xdist group | 67 |
| chemist account | 56 |
| external service, skip or mock | 8 |
| extra role accounts or users | 6 |

## Stock effect

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-045 | Negative stock allowed | allow negative stock->add item with 0 or neg stock | item should add in the grid | any trade | Ajay row 45 |
| AJ-046 | Negative stock not allowed | allow negative stock->add item with 0 or neg stock | item should not add in the grid | any trade | Ajay row 46 |
| AJ-049 | Negative quantity | add item->put quantity in negative | warning should show and further process should not be allowed | any trade | Ajay row 49 |
| AJ-058 | Multi store | create multiple stores->specify the store in bill->add items from the store | items from the store should show and stock should deduct from there | any trade | Ajay row 58 |
| AJ-068 | Batch stock validation | Select batch having insufficient stock | Appropriate stock warning should appear | chemist account | Ajay row 68 |
| AJ-069 | Batch-wise stock deduction | Create bill with specific batch | Stock should deduct from selected batch only | chemist account | Ajay row 69 |
| AJ-109 | Modify saved bill quantity | Reopen bill → change quantity | Stock and invoice should update correctly | any trade | Ajay row 109 |
| AJ-112 | Modify saved bill batch | Reopen bill → change batch | Stock should reverse old batch and deduct new batch correctly | chemist account | Ajay row 112 |
| AJ-114 | Delete bill stock reversal | Create bill → note stock → delete bill | Stock should be restored correctly | any trade | Ajay row 114 |
| AJ-123 | Multi-store wrong stock | Select Store A → select item stocked only in Store B | Item/stock should be handled correctly | any trade | Ajay row 123 |
| AJ-124 | Store change after item | Select Store A → add item → change to Store B | Stock/location should update correctly | any trade | Ajay row 124 |
| AJ-125 | Store-wise stock deduction | Create bill from Store A | Only Store A stock should reduce | any trade | Ajay row 125 |
| AJ-151 | Backdated billing | Enable backdated billing → create bill | Bill should save and stock/ledger should update correctly | changes tenant settings, xdist group | Ajay row 151 |
| AJ-169 | Zero-stock warning setting | Configure warning → sell zero-stock item | Correct warning should appear | changes tenant settings, xdist group | Ajay row 169 |
| AJ-170 | Negative-stock warning setting | Configure warning ON → sell into negative stock | Negative-stock warning should appear | changes tenant settings, xdist group | Ajay row 170 |
| AJ-171 | Negative-stock warning OFF | Configure warning OFF → sell into negative stock | Negative-stock warning should not appear | changes tenant settings, xdist group | Ajay row 171 |
| AJ-180 | Stock + multi-unit + batch | Select batch → sell using alternate unit | Correct converted quantity should deduct from selected batch | chemist account | Ajay row 180 |
| AJ-181 | Stock + promotion | Apply promotion → save bill | Correct promotional quantity/value and stock should update | any trade | Ajay row 181 |
| AJ-182 | Modification + promotion | Modify quantity on scheme bill | Scheme and stock should recalculate | any trade | Ajay row 182 |
| AJ-191 | stock negative allowed to yes | enable negative stock allowed->add item with negative stock | item should add to grid | changes tenant settings, xdist group | Ajay row 191 |
| AJ-192 | stock negative allowed to no | enable negative stock not allowed->add item with negative stock | item should not add to the grid | changes tenant settings, xdist group | Ajay row 192 |
| AJ-224 | indicate negative stock-yes | enable negative stock->set indicate negative stock to yes->add item with 0 stock | toaster for stock going negative should appear | changes tenant settings, xdist group | Ajay row 224 |
| AJ-225 | indicate negative stock-no | enable negative stock->set indicate negative stock to no->add item with 0 stock | toaster for stock going negative should not appear | changes tenant settings, xdist group | Ajay row 225 |
| ST-001 | Create Sale Challan | Create Challan with item & batch | Stock decreases in Item List, Batch List, and Item Register | chemist account | Stock row 2 |
| ST-002 | Modify Sale Challan (increase qty) | Edit existing Challan, increase qty | Additional stock is deducted | any trade | Stock row 3 |
| ST-003 | Modify Sale Challan (change batch) | Edit Challan and change batch | Old batch stock is restored, new batch stock deducted | chemist account | Stock row 4 |
| ST-004 | Delete Sale Challan | Delete a saved Challan | Stock is restored back to original | any trade | Stock row 5 |
| ST-005 | Convert Challan to Bill | Create Challan → Convert to Bill | No additional stock impact (already deducted) | any trade | Stock row 6 |
| ST-006 | Create Sale Bill directly | Select item, batch, qty and save bill | Stock is deducted immediately | chemist account | Stock row 7 |
| ST-008 | Delete Sale Bill | Delete bill after save | Stock is restored in full | any trade | Stock row 9 |
| ST-009 | Sale Return entry | Create return entry for billed item | Stock is added back to batch/item | chemist account | Stock row 10 |
| ST-010 | Sale Return Challan | Create return challan | Stock is increased for returned qty | any trade | Stock row 11 |
| ST-011 | Delete Sale Return | Delete return entry | Stock is reduced again (reversal of return) | any trade | Stock row 12 |
| ST-012 | Add new batch during sale | Create new batch in bill manually | New batch appears in Batch List with reduced stock | chemist account | Stock row 13 |
| ST-013 | Sell entire stock of a batch | Sell last quantity in batch | Batch stock becomes zero; batch still visible with 0 qty | chemist account | Stock row 14 |
| ST-014 | Try selling with zero stock | Add item with 0 qty left | System should block or warn (based on config) | any trade | Stock row 15 |
| ST-015 | Stock Issue entry | Create direct stock issue | Stock is reduced from item and batch | chemist account | Stock row 16 |
| ST-016 | Delete Stock Issue entry | Delete stock issue | Stock is added back | any trade | Stock row 17 |
| ST-017 | Sale Bill with future date | Create sale bill dated tomorrow | Today’s stock is unaffected; impact seen on future date | any trade | Stock row 18 |
| ST-018 | Sale Bill with backdate | Create bill with past date | Stock reduced as per past date and reflects in reports | any trade | Stock row 19 |
| ST-019 | Multiple batch usage | Add same item twice with different batches | Stock deducted from each respective batch | chemist account | Stock row 20 |
| ST-020 | Check stock impact in Item Register | Create sale/return/issue | Verify movement and balance in Item Register | any trade | Stock row 21 |
| ST-021 | Batch-wise movement check | Perform sale/return on batch | Check Batch List stock change accurately | chemist account | Stock row 22 |
| ST-022 | Partial Sale Return | Return only part of what was sold | Only returned quantity is added back to stock | any trade | Stock row 23 |
| ST-023 | Cancel challan before bill conversion | Cancel challan before it's billed | Stock restored fully | any trade | Stock row 24 |
| ST-024 | Convert Bill back to Challan | Convert sale bill back to challan | Stock reversal happens, like undo of sale | any trade | Stock row 25 |
| ST-025 | Change item in saved bill | Remove Item A, Add Item B | A's stock is restored, B’s is deducted | any trade | Stock row 26 |
| ST-026 | Verify zero stock batch visibility | Sell all stock from a batch | Batch still visible with 0 qty in Batch List | chemist account | Stock row 27 |
| ST-027 | Delete Partial converted challan | Convert Challan to Bill → Delete Challan | System should block or show impact warning | any trade | Stock row 28 |
| ST-029 | Sell item with duplicate batch name | Create two batches with same name (if allowed) | Verify stock is deducted from correct one | chemist account | Stock row 29 |
| ST-030 | Create return for item not in stock | Return without current stock available | System still allows return; stock added even if zero | any trade | Stock row 30 |
| ST-032 | Create Stock Issue and Sale both | Do stock issue and a bill for same item | Combined deduction shown in stock reports | any trade | Stock row 32 |
| ST-034 | Auto batch selection impact | Use auto batch suggestion during sale | System picks batch with earliest expiry / FIFO stock | chemist account | Stock row 34 |
| ST-035 | Sell item with negative stock allowed | Enable negative stock setting → Sell more than stock | Item stock goes negative and is shown accordingly | changes tenant settings, xdist group | Stock row 35 |
| SC-019 | If stock negative is off make store user should not able to enter stock greater then available stock(skip it negative stock setting is off) |  |  | changes tenant settings, xdist group | Sale checklist row 19 |
| SC-024 | While Creating a bill for any party, check if any existing sale order, challan, quotation are loading or not |  |  | any trade | Sale checklist row 24 |
| SC-026 | If sale rate is more than M.R.P make sure user should not able sell stock |  |  | any trade | Sale checklist row 26 |
| SC-031 | Check Real time stock updatation |  |  | any trade | Sale checklist row 31 |
| SC-035 | Check whole convert process quotation to order to challan to bill. Also check all discounts and values are loading properly |  |  | any trade | Sale checklist row 35 |
| SC-046 | Real Time Stock Calculation Check After Load Prescription and Last Bill Record etc. |  |  | chemist account | Sale checklist row 46 |
| SC-080 | Negative Cases Checks in Transactions Times.With Item Wise Negative Conditions Also |  |  | any trade | Sale checklist row 80 |
| SC-091 | check stock on item list, batch list , item register |  |  | chemist account | Sale checklist row 91 |
| PC-007 | after selecting party |  | If Some Pending order,Challan is created on that perticular party is created then window will open | any trade | Purchase checklist row 7 |
| PC-008 | If user select any Order ,Challan |  | 1) Item will load of thar pertucular Order,Challn in new window . From that window user can select Item | any trade | Purchase checklist row 8 |
| PC-009 | If Item selected from Order,Challan Window then pertucular Item loaded in transaction grid |  | 1) User can not add more item | any trade | Purchase checklist row 9 |
| PC-047 | After Bill Save |  | 1) Stock Updated in Item Batch and Item list | chemist account | Purchase checklist row 47 |

## Discount and scheme

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-013 | Discount calculation | add item->add quantity->add discounts | amount and invoice should be calculated correctly | any trade | Ajay row 13 |
| AJ-016 | Bill discount | add item-> apply bill discount 1 | invoice should calculate correctly | any trade | Ajay row 16 |
| AJ-017 | Bill discount2 | add item-> apply bill discount 2 | invoice should calculate correctly | any trade | Ajay row 17 |
| AJ-018 | Bill discount amount | add item-> apply bill discount amount | invoice should calculate correctly | any trade | Ajay row 18 |
| AJ-034 | Change discounts | add item ->add discounts->change discounts | item amount and invoice should changel | any trade | Ajay row 34 |
| AJ-051 | Sale promotion | create scheme->add item with scheme or bill amount as per scheme | scheme should apply | any trade | Ajay row 51 |
| AJ-098 | Discount percentage | Add item → apply percentage discount | Discount and net amount should calculate correctly | any trade | Ajay row 98 |
| AJ-099 | Multiple discounts | Add item → apply discount 1 + discount 2 | Sequential/combined discount should calculate correctly | any trade | Ajay row 99 |
| AJ-100 | Discount greater than amount | Apply discount greater than item amount | System should validate/prevent invalid amount | any trade | Ajay row 100 |
| AJ-101 | Bill discount + item discount | Apply both discounts | Both should calculate according to configured sequence | changes tenant settings, xdist group | Ajay row 101 |
| AJ-102 | Discount after quantity change | Add discount → change quantity | Discount and invoice total should recalculate | any trade | Ajay row 102 |
| AJ-103 | Discount after rate change | Add discount → change rate | Discount and invoice total should recalculate | any trade | Ajay row 103 |
| AJ-111 | Modify saved bill discount | Reopen bill → change discount | Discount and total should update correctly | any trade | Ajay row 111 |
| AJ-131 | Sale promotion not applicable | Create scheme for another item → bill different item | Scheme should not apply | any trade | Ajay row 131 |
| AJ-132 | Sale promotion quantity slab | Create slab scheme → sell below/above slab | Correct scheme should apply | any trade | Ajay row 132 |
| AJ-133 | Sale promotion modification | Apply scheme → change quantity | Scheme should recalculate | any trade | Ajay row 133 |
| AJ-134 | Sale promotion removal | Apply scheme → remove/rechange item | Scheme should be removed/recalculated | any trade | Ajay row 134 |
| AJ-135 | Net scheme boundary value | Configure scheme threshold → bill exactly threshold | Scheme should apply correctly | changes tenant settings, xdist group | Ajay row 135 |
| AJ-136 | Net scheme below threshold | Bill below threshold | Net scheme should not apply | any trade | Ajay row 136 |
| AJ-137 | Net scheme above threshold | Bill above threshold | Net scheme should apply correctly | any trade | Ajay row 137 |
| AJ-138 | Last deal no history | Select item with no previous deal | System should handle empty history correctly | any trade | Ajay row 138 |
| AJ-139 | Last deal party-wise | Configure party-wise last deal → select party/item | Correct party-specific previous deal should appear | changes tenant settings, xdist group | Ajay row 139 |
| AJ-210 | net scheme -allowed | enable net scheme->apply lot rate by scheme | net scheme should show at the bottom | changes tenant settings, xdist group | Ajay row 210 |
| AJ-211 | net scheme -not allowed | disable net scheme->apply lot rate by scheme | net scheme will not show at the bottom | changes tenant settings, xdist group | Ajay row 211 |
| AJ-213 | bill -item discount config- vol disc in lumpsum | choose lumpsum for vol discounts->select item->apply discounts | amount should calculate correctly | any trade | Ajay row 213 |
| AJ-214 | bill -item discount config- vol disc in percentage | choose percentage for vol discounts->select item->apply discounts | amount should calculate correctly | any trade | Ajay row 214 |
| AJ-215 | bill-item discount config- vol disc in perunit | choose perunit for vol discounts->select item->apply discounts | amount should calculate correctly | any trade | Ajay row 215 |
| AJ-217 | amount cal in bill-rate*qty | set amount calculation as rate*qty->add item->apply discounts | amount should show without discounts | any trade | Ajay row 217 |
| AJ-218 | amount cal in bill-rate*qty-discount | set amount calculation as rate*qty-discounts->add item->apply discounts | amount should show with discounts | any trade | Ajay row 218 |
| SC-020 | Check for Volume discount(Lumpsum, percentage ,perunit) if it's calculation is correct or not, according to controlroom setting |  |  | changes tenant settings, xdist group | Sale checklist row 20 |
| SC-021 | Verify if bill discount percentage and Amount both is working properly or not |  |  | any trade | Sale checklist row 21 |
| SC-023 | If the scheme is applicable on any product check if it is working fine (Item, Bill Value , Combo Offer , Buy X and Get Y, Rate Wise, No Scheme) under all these conditions |  |  | any trade | Sale checklist row 23 |
| SC-039 | After Applying Multiple Discounts(Special Dis-Party Wise Agency Dis-Agency Wise Dis-Item Wise Dis).Check Final Discount calculated |  |  | any trade | Sale checklist row 39 |
| SC-042 | Check last deal is loading properly or not |  |  | any trade | Sale checklist row 42 |
| SC-059 | Check if the Last Deal in sales settings (Itemwise/No) is functioning properly |  |  | changes tenant settings, xdist group | Sale checklist row 59 |
| SC-060 | Check net Scheme after (enabling /disabling) if it is working properly or not |  |  | any trade | Sale checklist row 60 |
| SC-061 | Check the amount calculation on billing (Rate * Quantity / Rate * Quantity - Discount / Net Amount) and verify the functioning of each condition |  |  | any trade | Sale checklist row 61 |
| SC-076 | Verify Update Changed Discount under all the given conditions |  |  | any trade | Sale checklist row 76 |
| SC-079 | Check Lot Rate Calculation, Ensure that it is working fine |  |  | changes tenant settings, xdist group | Sale checklist row 79 |
| SC-086 | Check Reverse Scheme Calculations |  |  | any trade | Sale checklist row 86 |
| SC-087 | Check Free Deal in Item Master Check All Conditions All Scheme,Whole scheme,All Scheme And No Scheme Calculations. |  |  | any trade | Sale checklist row 87 |
| SC-089 | Check Free deal if Given In Decimals Amount Calculations |  |  | any trade | Sale checklist row 89 |
| SC-090 | Check Lot Rate Calculations |  |  | changes tenant settings, xdist group | Sale checklist row 90 |
| PC-028 | After entring Purchase Rate |  | Focus goes to Discount Cell if enabled from controll room | changes tenant settings, xdist group | Purchase checklist row 28 |

## GST and tax

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-002 | Create new sale bill with single item | open bill-> add single item-> save | Bill should be created successfully | any trade | Ajay row 2 |
| AJ-003 | Create new sale bill with multiple items | open bill-> add multiple items-> save | Bill should be created successfully | any trade | Ajay row 3 |
| AJ-014 | GST Calculation (Inclusive calculation) | change calculation to inclusive->add taxable items | invoice,CGST and SGST or IGST should calculate correctly | any trade | Ajay row 14 |
| AJ-015 | GST Calculation (Exclusive calculation) | change calculation to exclusive->add taxable items | invoice,CGST and SGST or IGST should calculate correctly | any trade | Ajay row 15 |
| AJ-048 | Zero quantity | add item->put quantity as 0 | warning should show and further process should not be allowed | any trade | Ajay row 48 |
| AJ-073 | Customer change after item entry | Add items → change customer | Applicable rate, discount, tax and ledger values should recalculate correctly | any trade | Ajay row 73 |
| AJ-074 | Sale type change | Add items → change sale type | Applicable tax/rate should recalculate correctly | any trade | Ajay row 74 |
| AJ-075 | Taxable + exempt items | Add taxable and exempt items | Tax should calculate only for applicable items | any trade | Ajay row 75 |
| AJ-076 | Taxable + nil-rated items | Add taxable and nil-rated items | GST should calculate correctly | any trade | Ajay row 76 |
| AJ-091 | Taxable + non-GST items | Add taxable and non-GST items | GST should not calculate for non-GST items | any trade | Ajay row 91 |
| AJ-092 | CGST + SGST calculation | Select intra-state party → add taxable item | Correct CGST and SGST should calculate | any trade | Ajay row 92 |
| AJ-093 | IGST calculation | Select inter-state party → add taxable item | Correct IGST should calculate | any trade | Ajay row 93 |
| AJ-094 | GST rate change | Add item → change GST rate | Tax and invoice total should recalculate | any trade | Ajay row 94 |
| AJ-095 | GST exemption | Add GST-exempt item | GST should be zero | any trade | Ajay row 95 |
| AJ-096 | Round-off calculation | Create bill resulting in decimal paise | Round-off should calculate correctly | any trade | Ajay row 96 |
| AJ-097 | Round-off setting ON/OFF | Change round-off setting → create bill | Total should behave according to setting | changes tenant settings, xdist group | Ajay row 97 |
| AJ-108 | Modify saved bill | Save bill → reopen → modify → save | Modified bill should save successfully | any trade | Ajay row 108 |
| AJ-110 | Modify saved bill rate | Reopen bill → change rate | Amount/tax/total should update correctly | any trade | Ajay row 110 |
| AJ-129 | Additional charge tax | Add taxable additional charge | Applicable GST should calculate correctly | any trade | Ajay row 129 |
| AJ-174 | Inclusive + discount | Inclusive GST → apply item discount | Tax and net amount should calculate correctly | any trade | Ajay row 174 |
| AJ-175 | Exclusive + discount | Exclusive GST → apply item discount | Tax and net amount should calculate correctly | any trade | Ajay row 175 |
| AJ-176 | Inclusive + bill discount | Inclusive GST → apply bill discount | GST and invoice total should calculate correctly | any trade | Ajay row 176 |
| AJ-177 | Exclusive + bill discount | Exclusive GST → apply bill discount | GST and invoice total should calculate correctly | any trade | Ajay row 177 |
| AJ-178 | GST + additional charges | Add taxable item → add additional charge | GST and total should calculate according to configuration | any trade | Ajay row 178 |
| AJ-179 | GST + round-off | Create taxable bill → enable round-off | Tax, round-off and grand total should be correct | changes tenant settings, xdist group | Ajay row 179 |
| AJ-188 | Select inclusive | select inclusive as calculation type->add taxable item | invoice calculation should be as per inclusive | changes tenant settings, xdist group | Ajay row 188 |
| AJ-189 | Seelct exclusive | select exclusive as calculation type->add taxable item | invoice calculation should be as per exclusive | changes tenant settings, xdist group | Ajay row 189 |
| SC-022 | Check tax information CGST and SGST  And Central Case IGST, CESS it's calculation is correct or not, |  |  | any trade | Sale checklist row 22 |
| SC-027 | Verify the invoice value to check whether the total is correct and if the tax has been added properly or not |  |  | any trade | Sale checklist row 27 |
| SC-028 | After creating sale bill , click on save as draft(Make sure enable the settings for draft) and check if bill save is successfully or not. |  |  | changes tenant settings, xdist group | Sale checklist row 28 |
| SC-044 | Check if the bill created by the user is saved in the database successfully |  |  | any trade | Sale checklist row 44 |
| SC-056 | Calcualtion type in sale in settings(Exclusive/Inclusive) are working properly or not |  |  | changes tenant settings, xdist group | Sale checklist row 56 |
| SC-081 | Check Cess Calculatons In Cess Percentage And Cess Amount Both Cases. |  |  | any trade | Sale checklist row 81 |
| SC-085 | Counter Sale Billing Process Check Covered Counter Sale Real Time and Counter Sale To Bill Loading Process |  |  | any trade | Sale checklist row 85 |
| PC-041 | After Mode Of Pament OR GST Summary |  | Gst Will Applied. Below are cases | any trade | Purchase checklist row 41 |

## Bill lifecycle (create, modify, delete)

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-005 | Sale bill without customer | from setting enable customer name and mandatory->  make bill without entering customer -> save | Bill should not save and a warning must show | changes tenant settings, xdist group | Ajay row 5 |
| AJ-020 | Modify bill by changing item | create bill->modify item to another->save | item should be updated along with invoice | any trade | Ajay row 20 |
| AJ-021 | Modify bill by changing quantity | create bill->modify quantity to another->save | quantity should be updated along with invoice | any trade | Ajay row 21 |
| AJ-022 | Modify bill by deleting item | create bill-> modify->delete item | item should be updated along with invoice | any trade | Ajay row 22 |
| AJ-024 | Change item | add item->change it to another item | item should be updated along with | any trade | Ajay row 24 |
| AJ-025 | Change quantity | add item->change quantity to another | quantity should change accordingly | any trade | Ajay row 25 |
| AJ-029 | Duplicate barcode | add barcode with multiple items | multiple items's window should appear | any trade | Ajay row 29 |
| AJ-030 | Save bill | create a bill-> save | toaster to save should appear, bill should be visible in list | any trade | Ajay row 30 |
| AJ-036 | Delete bill | create bill->open bill list->delete the created bill | bill deletion toaster should appear, and bill should disappear form the list | any trade | Ajay row 36 |
| AJ-062 | Save bill with blank rate | Add item → remove/blank rate → save | Appropriate rate validation should appear | any trade | Ajay row 62 |
| AJ-063 | Save bill with zero rate | Add item → set rate 0 → save | Warning should appear as per setting | changes tenant settings, xdist group | Ajay row 63 |
| AJ-064 | Blank quantity | Add item → remove quantity → save | Quantity validation should appear | any trade | Ajay row 64 |
| AJ-065 | Duplicate item in bill | Add same item twice | System should merge/add separate row according to configuration | any trade | Ajay row 65 |
| AJ-072 | Customer credit limit | Create bill exceeding party credit limit | Credit-limit warning/block should appear according to setting | changes tenant settings, xdist group | Ajay row 72 |
| AJ-104 | Delete all items | Add multiple items → delete all | Grid should become empty and bill should not save | any trade | Ajay row 104 |
| AJ-105 | Delete first item | Add 3 items → delete first | Remaining items and totals should remain correct | any trade | Ajay row 105 |
| AJ-106 | Delete middle item | Add 3 items → delete middle | Remaining items and totals should remain correct | any trade | Ajay row 106 |
| AJ-107 | Delete last item | Add 3 items → delete last | Remaining items and totals should remain correct | any trade | Ajay row 107 |
| AJ-113 | Cancel modified bill | Open bill → make changes → cancel | Original bill should remain unchanged | any trade | Ajay row 113 |
| AJ-146 | Escape/cancel bill | Enter bill data → press cancel/escape | Unsaved data should be discarded according to confirmation | any trade | Ajay row 146 |
| AJ-147 | Bill number generation | Create multiple bills consecutively | Bill numbers should generate correctly without duplication | any trade | Ajay row 147 |
| AJ-148 | Bill number after deletion | Create → delete → create another bill | Numbering should follow configured sequence | changes tenant settings, xdist group | Ajay row 148 |
| AJ-149 | Duplicate bill number | Attempt duplicate bill number | System should prevent duplicate number | any trade | Ajay row 149 |
| AJ-152 | Backdated billing not allowed | Disable backdated billing → enter old date | Bill should not save | changes tenant settings, xdist group | Ajay row 152 |
| AJ-168 | Duplicate save | Enter bill → click save multiple times quickly | Only one bill should be created | any trade | Ajay row 168 |
| AJ-223 | indicate billing rate is 0 | select item->set rate to 0->save | toaster for invoice zero should appear | changes tenant settings, xdist group | Ajay row 223 |
| SC-002 | Click on create button and check grid is properly initialized |  |  | any trade | Sale checklist row 2 |
| SC-075 | Verify Update Changed Rate (Price List / Ask/ w/o Price List) |  |  | any trade | Sale checklist row 75 |
| SC-092 | check item and bill dscount add, modify, remove |  |  | any trade | Sale checklist row 92 |
| PC-002 | Click On Plus + F2 Button |  | New Blank  Page Render + Load un saved bill (Last 3 days) | any trade | Purchase checklist row 2 |

## Settings toggles

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-006 | Select item | select items by barcode | items should appear in the grid | any trade | Ajay row 6 |
| AJ-007 | Select item | select items by item window | items should appear in the grid | any trade | Ajay row 7 |
| AJ-008 | Quantity validation | select item->enter quantity | amount should be calculated as per the quantity | changes tenant settings, xdist group | Ajay row 8 |
| AJ-084 | Item inactive | Select inactive/blocked item | Item should not be selectable | any trade | Ajay row 84 |
| AJ-085 | Party inactive | Select inactive customer | Customer should not be selectable / appropriate warning | any trade | Ajay row 85 |
| AJ-172 | Zero-rate warning setting | Configure zero-rate indication → sell at zero | Warning/toaster should appear | changes tenant settings, xdist group | Ajay row 172 |
| AJ-173 | Zero-rate warning OFF | Disable indication → sell at zero | Warning should not appear | changes tenant settings, xdist group | Ajay row 173 |
| AJ-197 | ask party in retail billing-ask | enable setting to ask->open bill | party selection window shpuld appear | changes tenant settings, xdist group | Ajay row 197 |
| AJ-198 | ask party in retail billing-don’t ask | enable setting to don’t ask->open bill | party should be selected by default | changes tenant settings, xdist group | Ajay row 198 |
| AJ-199 | ask party in retail billing-ask on spacebar | enable setting to ask on spacebar->open bill | party should be selected by default and pressing space should open list | changes tenant settings, xdist group | Ajay row 199 |
| AJ-220 | ask sale type at time of billing -yes | select yes for sale type | sale type should appear in the header | changes tenant settings, xdist group | Ajay row 220 |
| AJ-221 | ask sale type at time of billing -no | select no for sale type | sale type should not appear in the header | changes tenant settings, xdist group | Ajay row 221 |
| SC-004 | Check bill date should be managed by setting |  |  | changes tenant settings, xdist group | Sale checklist row 4 |
| SC-006 | Check when enter on bill date focus should be on multi-series window if enable else on ledger list |  |  | changes tenant settings, xdist group | Sale checklist row 6 |
| SC-030 | Check User not able to sell item in Loss.(if warning disable) |  |  | changes tenant settings, xdist group | Sale checklist row 30 |
| SC-045 | Last Bill Setting Checks According Ledger Wise |  |  | changes tenant settings, xdist group | Sale checklist row 45 |
| SC-047 | Check all the settings in Sale bill working properly |  |  | changes tenant settings, xdist group | Sale checklist row 47 |
| SC-049 | After logging in/logging out, check that the settings remain the same. |  |  | changes tenant settings, xdist group | Sale checklist row 49 |
| SC-057 | Check Ask Party in Retail Billing (Ask/Don’t Ask/Ask on SpaceBar) ensure that they are working under all these conditions |  |  | changes tenant settings, xdist group | Sale checklist row 57 |
| SC-062 | Verify the functioning of Ask Bill No. under all conditions |  |  | changes tenant settings, xdist group | Sale checklist row 62 |
| SC-063 | Verify the functioning of Ask Sale Type at the time of Billing under all conditions |  |  | changes tenant settings, xdist group | Sale checklist row 63 |
| SC-064 | Check Ask Net Rate (Ask always/ Ask  on * key/No) under all these conditions |  |  | changes tenant settings, xdist group | Sale checklist row 64 |
| SC-065 | Check Ask Order No. and Order Date if they are working properly or  not |  |  | changes tenant settings, xdist group | Sale checklist row 65 |
| SC-067 | Verify the 'MR Required' setting after enabling or disabling it, and ensure it is working properly |  |  | changes tenant settings, xdist group | Sale checklist row 67 |
| SC-068 | Pick MR from(Loop/Master/Direct )verify all these settings |  |  | changes tenant settings, xdist group | Sale checklist row 68 |
| SC-069 | Check if "Indicate if Item Repeated in Bill" under all the given (Indicate/Ask Forcefully/No) conditions |  |  | changes tenant settings, xdist group | Sale checklist row 69 |
| SC-078 | Verify Default Billing Rate setting ensure that it is working properly under all the conditions |  |  | changes tenant settings, xdist group | Sale checklist row 78 |
| PC-013 | On Item cell |  | Item list open user can select item from that window | any trade | Purchase checklist row 13 |
| PC-022 | after entering unit |  | Focus goes to Free cell (If enabled from controll room) | changes tenant settings, xdist group | Purchase checklist row 22 |

## Batch and expiry

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-011 | Rate auto pick batchwise | set rate auto to batchwise->add item in bill | rate should show in grid as per batch rate | chemist account | Ajay row 11 |
| AJ-027 | Batch selection | select item with multiple batches in the grid | batch grid should appear with all batches | chemist account | Ajay row 27 |
| AJ-028 | Expiry validation | select item with an expired batch->select expired batch | selecting expired batch will show warning,and wont be selected | chemist account | Ajay row 28 |
| AJ-066 | Duplicate batch in bill | Add same item and same batch twice | Batch quantity/rows should behave according to configuration | chemist account | Ajay row 66 |
| AJ-067 | Different batch same item | Add same item with two batches | Both batches should appear with correct quantities/rates | chemist account | Ajay row 67 |
| AJ-070 | Expired batch with allowed setting | Configure expired batch allowance → select expired batch | Batch should be selectable only according to setting | chemist account | Ajay row 70 |
| AJ-071 | Near-expiry batch | Select batch nearing expiry | Expiry warning should appear if configured | chemist account | Ajay row 71 |
| AJ-140 | Last deal batch-wise | Select batch → verify history | Correct batch history should appear | chemist account | Ajay row 140 |
| AJ-201 | last deal in sale-batchwise | select last deal as batchwise->add item with multiple batches | previous deals of the batch should appear | chemist account | Ajay row 201 |
| AJ-202 | last deal in sale-itemwise | select last deal as itemwise->add item with multiple batches | previous deals of the item should appear | chemist account | Ajay row 202 |
| ST-007 | Modify Sale Bill (change batch) | Edit bill, switch to another batch | Old batch restored, new one deducted | chemist account | Stock row 8 |
| ST-033 | Save sale with invalid batch name | Mistype batch manually | System should validate and block/save as new batch | chemist account | Stock row 33 |
| SC-015 | After selecting item the focus navigate to batch column(if enable) else on expiry(if enable) else on quantity |  |  | chemist account | Sale checklist row 15 |
| SC-016 | If batch enable focus will move to batch window and will select batch |  |  | chemist account | Sale checklist row 16 |
| SC-017 | After batch selection  focus will navigate to quantity column |  |  | chemist account | Sale checklist row 17 |
| SC-025 | After Selecting any item in bill check that sale rate picks automatically. Check Both Case Item Wise And Batch Wise Rates. |  |  | chemist account | Sale checklist row 25 |
| SC-029 | Check User not able to sell Prohbited and expiry item |  |  | chemist account | Sale checklist row 29 |
| SC-033 | Check Rate Picking (itemwise/Batch Wise) |  |  | chemist account | Sale checklist row 33 |
| SC-037 | Verify Barcode Scanning  While billing Master wise & Batch wise Barcode with  parameter trade |  |  | chemist account | Sale checklist row 37 |
| SC-066 | Check the configuration of Expiry & MFG4 to ensure they are working properly. |  |  | chemist account | Sale checklist row 66 |
| SC-071 | Verify Batch window index on(Expiry/MFG Date/ FIFO Date/ Batch Name) under all these conditons |  |  | chemist account | Sale checklist row 71 |
| SC-074 | Check Free Deal from(Master/Batch/Manual/Lot/Lot& Free) under these conditions |  |  | chemist account | Sale checklist row 74 |
| SC-095 | check rate from master, batch, parameter(manual and barcode) |  |  | chemist account | Sale checklist row 95 |
| PC-014 | After selecting Item |  | Focus goes to batch cell user can enter batch name | chemist account | Purchase checklist row 14 |
| PC-015 | After Entering batch name |  | Focus goes to QTY cell | chemist account | Purchase checklist row 15 |
| PC-033 | After Discount |  | Batch Window will open | chemist account | Purchase checklist row 33 |
| PC-039 | After Batch |  | 1) If user press Tab for saving bill Gst summary will display | chemist account | Purchase checklist row 39 |

## General

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-010 | Rate auto pick itemwise | set rate auto to item master->add item in bill | rate should show in grid as per item master | any trade | Ajay row 10 |
| AJ-047 | Decimal allowed | add item with decimal not allowed | waring should show | any trade | Ajay row 47 |
| AJ-150 | Date validation | Enter invalid/future/backdated date | Date should be validated according to configuration | any trade | Ajay row 150 |
| SC-005 | Check back date bill  conditions |  |  | any trade | Sale checklist row 5 |
| SC-009 | Check pagination is working on party window |  |  | any trade | Sale checklist row 9 |
| SC-010 | Check search party is working fine and make sure api call should be limited |  |  | any trade | Sale checklist row 10 |
| SC-032 | Check Real time Ledger Balance update |  |  | any trade | Sale checklist row 32 |
| SC-036 | Verify Invoice templates(Thermal,Full page,Pharma,chemist billing, general, landscape, Dmp half page , Dmp Full page ,Bill to ship to , Parameter Page) |  |  | any trade | Sale checklist row 36 |
| SC-038 | While Selecting party name and product name check search bar is functioning properly |  |  | any trade | Sale checklist row 38 |
| SC-043 | Check that no API is called redundantly. |  |  | any trade | Sale checklist row 43 |
| SC-050 | Verify if the custom filter is working properly |  |  | any trade | Sale checklist row 50 |
| SC-053 | Check Bulk action button if its functionality working properly or not |  |  | any trade | Sale checklist row 53 |
| SC-054 | Verify action column buttons if they are working properly or not |  |  | any trade | Sale checklist row 54 |
| SC-055 | Check all the calculations and disocunts on E-way bill |  |  | any trade | Sale checklist row 55 |
| SC-058 | Check Cursor Wait on (All/Qty) are working properly |  |  | any trade | Sale checklist row 58 |
| SC-070 | Check  if Billing Rate is Zero is working properly |  |  | any trade | Sale checklist row 70 |
| SC-072 | Verify Free Quantity Required in Sale functioning Properly |  |  | any trade | Sale checklist row 72 |
| SC-073 | Verify Free Quantity Required in Decimal working under all the required conditions |  |  | any trade | Sale checklist row 73 |
| SC-077 | Check the configuration  of Minimum level crossed, ensure that it is working properly |  |  | any trade | Sale checklist row 77 |
| SC-082 | Check Multi Series Billing All Cases Include Group Wise,Agency Wise etc. |  |  | any trade | Sale checklist row 82 |
| SC-084 | Check Agency Wise Billing,Salt Wise Billing ,Substitute Wise Billing And Category Wise Billing in Transactions Times. |  |  | any trade | Sale checklist row 84 |
| SC-088 | Check * Key Net Rate Calculations |  |  | any trade | Sale checklist row 88 |
| SC-094 | check loss indication window |  |  | any trade | Sale checklist row 94 |

## External send/print (WhatsApp, email, SMS, print)

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-032 | Print bill | create bill->save->print preview | data entered in the grid should be same as printed | any trade | Ajay row 32 |
| AJ-053 | Share on whatsapp | create bill->share on whatsapp | bill should be shared | external service, skip or mock | Ajay row 53 |
| AJ-054 | Share on email | create bill->share on email | bill should be shared | external service, skip or mock | Ajay row 54 |
| AJ-055 | Share on SMS | create bill->share on SMS | bill should be shared | external service, skip or mock | Ajay row 55 |
| AJ-056 | Share in bulk | share multiple created bills on whatsapp,email or SMS | all bills should be shared | external service, skip or mock | Ajay row 56 |
| AJ-153 | Print after modification | Save → modify → print | Printed bill should contain latest data | any trade | Ajay row 153 |
| AJ-154 | Reprint bill | Open saved bill → print again | Same bill data should print correctly | any trade | Ajay row 154 |
| AJ-155 | Print multiple bills | Select multiple bills → print | Correct bills should be printed | any trade | Ajay row 155 |
| AJ-156 | WhatsApp without mobile | Select party without mobile → share | Appropriate validation should appear | external service, skip or mock | Ajay row 156 |
| AJ-157 | Email without email ID | Select party without email → share | Appropriate validation should appear | external service, skip or mock | Ajay row 157 |
| AJ-158 | SMS without mobile | Select party without mobile → share | Appropriate validation should appear | external service, skip or mock | Ajay row 158 |
| AJ-159 | Share modified bill | Modify saved bill → share | Latest bill should be shared | any trade | Ajay row 159 |
| AJ-160 | Bulk share selected bills | Select specific bills → bulk share | Only selected bills should be shared | any trade | Ajay row 160 |
| AJ-161 | Bulk share all bills | Select all → share | All selected bills should be shared | any trade | Ajay row 161 |
| ST-031 | Print stock report after transactions | Perform sale and return | Run Item/Batch/Item Register report → Reflects movement correctly | chemist account | Stock row 31 |
| SC-051 | Check if the upload, print, email, WhatsApp, and export buttons are functioning properly |  |  | external service, skip or mock | Sale checklist row 51 |
| SC-052 | Check printout and print after modification details |  |  | any trade | Sale checklist row 52 |
| PC-051 | Extras |  | 1) User can print bill from purchase bill list | any trade | Purchase checklist row 51 |

## Payment (MOP)

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-038 | Mode of payment | enable MOP->create and save bill->add partial payment | partial payment should save and status should show partial | changes tenant settings, xdist group | Ajay row 38 |
| AJ-039 | Mode of payment | enable MOP->create and save bill->add full payment | full payment should save and status should show paid | changes tenant settings, xdist group | Ajay row 39 |
| AJ-040 | Mode of payment | enable MOP->create and save bill->add payment to different ledger | payment should save | changes tenant settings, xdist group | Ajay row 40 |
| AJ-041 | add and remove ledger from mode of payment window | on mode of payment window click on settings add ledger and also remove ledger |  | changes tenant settings, xdist group | Ajay row 41 |
| AJ-115 | Delete bill with payment | Create paid bill → delete | Payment/ledger and bill deletion should behave correctly | any trade | Ajay row 115 |
| AJ-116 | Delete bill with partial payment | Create partial-paid bill → delete | System should handle payment and deletion correctly | any trade | Ajay row 116 |
| AJ-117 | MOP multiple ledgers | Enable MOP → select multiple payment ledgers | Amount should distribute correctly | changes tenant settings, xdist group | Ajay row 117 |
| AJ-118 | MOP amount mismatch | Enter payment less/more than invoice | Appropriate balance/validation should appear | any trade | Ajay row 118 |
| AJ-119 | MOP zero payment | Open MOP → enter zero | System should handle according to configuration | any trade | Ajay row 119 |
| AJ-120 | MOP payment modification | Save bill → modify payment | Payment and status should update correctly | any trade | Ajay row 120 |
| AJ-121 | MOP cash + bank payment | Create bill → split payment between cash/bank | Both payments should save correctly | any trade | Ajay row 121 |
| AJ-122 | MOP ledger inactive | Configure inactive ledger → open MOP | Inactive ledger should not be selectable | changes tenant settings, xdist group | Ajay row 122 |
| AJ-183 | Modification + MOP | Modify paid bill | Payment/balance status should remain consistent | any trade | Ajay row 183 |
| AJ-184 | Delete + MOP | Delete paid bill | Payment and ledger entries should reverse correctly | any trade | Ajay row 184 |
| AJ-194 | mode of payment required | enable MOP->create and save bill | MOP window should appear | changes tenant settings, xdist group | Ajay row 194 |
| AJ-195 | mode of payment not required | disable MOP->create and save bill | MOP window should not appear | changes tenant settings, xdist group | Ajay row 195 |
| SC-034 | Check Mode of Payments with multiple modes |  |  | any trade | Sale checklist row 34 |

## Keyboard and navigation

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-145 | Keyboard navigation | Open bill → navigate using Tab/Enter/shortcuts | Focus should move correctly | any trade | Ajay row 145 |
| SC-003 | Check focus should be on bill date |  |  | any trade | Sale checklist row 3 |
| SC-008 | When party window is open make sure focus on search box and last selected party |  |  | any trade | Sale checklist row 8 |
| SC-012 | After party selection focus navigate to product |  |  | any trade | Sale checklist row 12 |
| SC-013 | After that item  list window will pop up and focus should be on search box at item list |  |  | any trade | Sale checklist row 13 |
| SC-014 | and  focus on last selected item |  |  | any trade | Sale checklist row 14 |
| SC-048 | Check F8 voucher posting |  |  | any trade | Sale checklist row 48 |
| SC-083 | Check Profit Calculations in Tab Keys And Alt+F10 Keys.Check Both Profit in Rs And Percentage. |  |  | any trade | Sale checklist row 83 |
| SC-093 | check alt+f10 profit window |  |  | any trade | Sale checklist row 93 |
| PC-003 | Focus gone to bill date |  | 1) If Curent fincial year(Curent Date will render) | any trade | Purchase checklist row 3 |
| PC-005 | after enter on bill date |  | Focus go to party control | any trade | Purchase checklist row 5 |
| PC-012 | If Order , Chalan Is not selected |  | Then Afetr party selected focus goes to Item Cell | any trade | Purchase checklist row 12 |
| PC-025 | After entring Free |  | Focus goes to rate cell | any trade | Purchase checklist row 25 |

## Patient/doctor (chemist)

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-141 | Patient doctor mandatory | Enable mandatory → leave doctor blank | Bill should not save | chemist account | Ajay row 141 |
| AJ-142 | Patient doctor optional | Disable mandatory → leave doctor blank | Bill should save | chemist account | Ajay row 142 |
| AJ-143 | Patient doctor at start | Mandatory at start → open bill | Focus should move to patient/doctor field | chemist account | Ajay row 143 |
| AJ-144 | Patient doctor at save | Mandatory at save → leave blank → save | Validation should appear at save | chemist account | Ajay row 144 |
| AJ-204 | pat-doc must-yes | select pat-doc must to yes->skip pat-doc and create bill->save | bill should not save and should show warning | chemist account | Ajay row 204 |
| AJ-205 | pat-doc must-no | select pat-doc must to no->skip pat-doc and create bill->save | bill should save | chemist account | Ajay row 205 |
| AJ-207 | pat- doc at -start | make pat-doc mandatory and start->fill party->press enter | focus should come on patient doctore and should not move without filling | chemist account | Ajay row 207 |
| AJ-208 | pat- doc at -save | make pat-doc mandatory and save->fill party->press enter->skip pat doc->save | focus should not come on patient doctor and ask to fill while saving the bill | chemist account | Ajay row 208 |
| SC-041 | Check for Pending prescription list(Chemist) |  |  | chemist account | Sale checklist row 41 |

## Multi store and unit

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-042 | Multi unit quantity validation | add item with multi unit->verify quanitity | quantity should be shown as converted correctly | any trade | Ajay row 42 |
| AJ-043 | Multi unit amount validation | add item with multi unit->verify amount | amount should calculate correctly as per conversion | any trade | Ajay row 43 |
| SC-007 | Before Open party select window make sure bill no data and store data should be populated |  |  | any trade | Sale checklist row 7 |
| SC-011 | After party selection the focus should be on select store(if multi-store) else on product |  |  | any trade | Sale checklist row 11 |
| SC-018 | If multi-unit is enable first focus will move to unit 2 column after that unit1 column  (Control Room Base Work this) |  |  | changes tenant settings, xdist group | Sale checklist row 18 |
| SC-040 | Check if each branch of the store is billing correctly |  |  | any trade | Sale checklist row 40 |
| PC-016 | If user Enabled Multi unit in purchase |  | 1) If Item have multi unit user can enter QTY  in Unit 1 and Unit 2 both | changes tenant settings, xdist group | Purchase checklist row 16 |

## Permissions and users

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-162 | Authorization/permission | Login with user without sale-bill permission | Sale bill should not be accessible | extra role accounts or users | Ajay row 162 |
| AJ-163 | Delete permission | User without delete permission → delete bill | Delete option should be hidden/blocked | extra role accounts or users | Ajay row 163 |
| AJ-164 | Modify permission | User without modify permission → open bill | Modify should be blocked | extra role accounts or users | Ajay row 164 |
| AJ-165 | Rate permission | User without rate-change permission → modify rate | Rate modification should be blocked | extra role accounts or users | Ajay row 165 |
| AJ-166 | Discount permission | User without discount permission → apply discount | Discount should be blocked/validated | extra role accounts or users | Ajay row 166 |
| AJ-167 | Concurrent billing | Create bills from two users simultaneously | Bill numbers, stock and data should remain consistent | extra role accounts or users | Ajay row 167 |

## Additional charges

| ID | Scenario | Steps | Expected | Needs | Source |
|---|---|---|---|---|---|
| AJ-059 | Additional ledger | select ledger as additional charges->add additional charges | should be able to add more charges and invoice should calculate | changes tenant settings, xdist group | Ajay row 59 |
| AJ-126 | Additional charges percentage | Add additional charge as % | Charge and total should calculate correctly | any trade | Ajay row 126 |
| AJ-127 | Additional charges amount | Add fixed additional charge | Charge and total should calculate correctly | any trade | Ajay row 127 |
| AJ-128 | Multiple additional charges | Add multiple charges | All charges should calculate correctly | any trade | Ajay row 128 |
| AJ-130 | Remove additional charge | Add charge → remove charge | Invoice total should recalculate | any trade | Ajay row 130 |
