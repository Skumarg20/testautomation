from typing import ClassVar

from pages.accounting.accounting_menu import Screen
from pages.accounting.receipt_payment_voucher import ReceiptPaymentVoucher


class ReceiptPage(ReceiptPaymentVoucher):
    SCREEN: ClassVar[Screen] = "Receipt"
    BALANCE_SIGN: ClassVar[int] = -1
