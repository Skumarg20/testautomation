"""Sale > Return Challan: goods taken back against a sale, saved without a bill.

Factory `SaleReturnChallanFactory` (Model/TransactionFactory/sale.returnchallan.factory.ts): heading
"Sale Return Challan", number label "Challan No.", save message "Sale Return Challan Saved successfully!"
(:24-26), list route `/sale/salereturnchallan` (menu.component.ts:83). The menu text "Return Challan" and the
way the party and lines are entered are taken from the sale challan screen and are unverified live.
"""

from pages.sale.documents.challan import SaleChallan


class SaleReturnChallan(SaleChallan):
    menu = ("Sale", "Return Challan")
    number_label = "Challan No."
