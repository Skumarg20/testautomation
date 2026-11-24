from typing import ClassVar

from pages.accounting.accounting_menu import Screen
from pages.accounting.receipt_payment_voucher import ReceiptPaymentVoucher


class PaymentPage(ReceiptPaymentVoucher):
    SCREEN: ClassVar[Screen] = "Payment"
    BALANCE_SIGN: ClassVar[int] = 1
