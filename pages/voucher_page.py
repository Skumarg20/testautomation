"""
Receipt / Payment / Journal / Debit Note / Credit Note ke liye POM.

Ye Sale Bill se alag hain: inme item grid nahi hota, ledger aur amount hote
hain. Isliye TransactionForm se alag class -- warna ek hi class me do bilkul
alag cheezein ghusa deni padtin.
"""
from __future__ import annotations

from framework import safety
from framework.base_page import BasePage
from framework.screens import open_screen
from pages.transaction_form import TransactionForm, FormNotOpen


class VoucherPage(TransactionForm):
    SCREEN = ""
    TITLE = "Voucher"

    def __init__(self, bp: BasePage, screen: str | None = None):
        super().__init__(bp)
        if screen:
            self.SCREEN = screen

    @classmethod
    def open(cls, bp: BasePage, screen: str | None = None, verbose: bool = False):
        key = screen or cls.SCREEN
        if not open_screen(bp, key, verbose=verbose):
            raise FormNotOpen(f"'{key}' khul nahi paya. URL: {bp.page.url}")
        page = cls(bp, screen=key)
        page.clear_popups()
        return page

    def is_empty_list(self) -> bool:
        """
        Voucher ka "+" pehle LIST kholta hai, aur list khali ho to
        "No ... Created Yet" wala page dikhta hai. Us par form nahi hota.
        """
        try:
            body = self.page.inner_text("body") or ""
        except Exception:  # noqa: BLE001
            return False
        return "Created Yet" in body

    def create_from_empty(self):
        """Khali list se naya voucher banao."""
        for label in ("+ Create", "Create/F2", "Create"):
            try:
                b = self.page.get_by_role("button", name=label, exact=False).first
                if b.is_visible(timeout=1200):
                    safety.guarded_click(b, f"{self.SCREEN}.create", timeout=4000)
                    self.bp.settle()
                    self.clear_popups()
                    self.refresh()
                    return self
            except Exception:  # noqa: BLE001
                continue
        raise FormNotOpen(f"'{self.SCREEN}' me Create ka button nahi mila")
