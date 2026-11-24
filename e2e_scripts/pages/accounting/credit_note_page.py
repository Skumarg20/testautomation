from typing import ClassVar

from pages.accounting.accounting_menu import Screen
from pages.accounting.two_sided_voucher import TwoSidedVoucher


class CreditNotePage(TwoSidedVoucher):
    SCREEN: ClassVar[Screen] = "Credit Note"
