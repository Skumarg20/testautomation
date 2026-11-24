"""The texts the sale bill shows for the manual cases, each with the source line it comes from.

Sources are in newmarg-webangular20/src/app: `Globals/global.ts` (AlertMsg) and the processout component
(`Component/Transaction/InverntoryTransaction/processout.transaction.component.ts`), which is the sale bill.
"""

# global.ts:19007, raised when a rate of 0 is entered (processout.transaction.component.ts:12443-12445)
ZERO_RATE_ASKED = "Are you sure you want to go with 0 rate?"
# global.ts:19320, written after a count: "1 items has rate value 0. Accept?" (processout...ts:10364)
ZERO_RATE_AT_SAVE = "items has rate value 0. Accept?"
# global.ts:19322, raised by negativeAllowedNoCondition (processout...ts:12853-12857)
STOCK_GOING_NEGATIVE = "Stock going in negative!"
# global.ts:19337, "Salable stock <n>.": the quantity is cut to what the batch holds (processout...ts:12817)
SALABLE_STOCK = "Salable stock"
# global.ts:18995, checkQtyOrFreeHasValue (transactionin.component.ts:7733, shared grid rule)
QUANTITY_REQUIRED = "Quantity should be greater than 0!"
# global.ts:19306 and global.ts:19761, raised on save (processout...ts:10454-10457)
BACK_DATE_REFUSED = "Back Date Billing Not Allowed"
FUTURE_DATE_REFUSED = "Future Date Billing Not Allowed"
# global.ts:19332, dataCalculation.ts:1371-1373
BILL_DISCOUNT_ABOVE_GOODS = "Bill Discount Amount should be less than or equals to Goods Value"
# global.ts:19352 and global.ts:19350 (modeofpayment.component.ts:589-594, :527)
PAYMENT_ABOVE_BILL = "Please check total amount"
# global.ts:19349, raised by Common.service.ts:4412 when the shared mobile number is not given
WHATSAPP_NUMBER_MISSING = "Party Whatsapp Number not available."
