"""Sale Bill / Sale Return ka page object."""
from __future__ import annotations

from config.settings import settings
from framework import safety
from framework.base_page import BasePage
from framework.screens import open_screen
from pages import ag_grid
from pages.transaction_form import TransactionForm, FormNotOpen


class SaleBillPage(TransactionForm):
    SCREEN = "sale_bill"
    TITLE = "Sale Bill"

    @classmethod
    def open(cls, bp: BasePage, verbose: bool = False) -> "SaleBillPage":
        if not open_screen(bp, cls.SCREEN, verbose=verbose):
            raise FormNotOpen(f"{cls.TITLE} khul nahi paya. URL: {bp.page.url}")
        page = cls(bp)
        page.clear_popups()          # "Set Transaction Preferences" hata do
        page.refresh()               # popup ke baad suffix dobara
        return page

    # ---- item grid (ag-Grid) ----
    #
    # Grid ke input ka number ROW ka hai, tab ka nahi:
    #     #txt-tmp_barcode-0        pehli line
    #     #txt-unitToEnteredValue-0 uski quantity
    # Header ke field tab ka number rakhte hain (txtLedgerName27).
    # Do alag naming ek hi form me -- ye jaane bina automation atakti hai.

    def line_count(self) -> int:
        """Grid me kitni bhari hui line hain."""
        return ag_grid.line_count(self.page)

    def grid_rows(self) -> list[dict]:
        return ag_grid.filled_rows(self.page)

    def grid_columns(self) -> list[str]:
        """Is trade me grid me kaunse column hain."""
        return [c["id"] for c in ag_grid.columns(self.page)]

    def _cell(self, field: str, row: int):
        return self.page.locator(ag_grid.cell_id(field, row))

    def add_by_barcode(self, barcode: str, qty: float = 1,
                       rate: float | None = None,
                       discount: float | None = None, row: int = 0):
        """
        Barcode se item jodo -- sabse bharosemand tareeka.

        Naam se dhoondhna nazuk hai (spelling, aadha naam, "Not Found"),
        barcode ek hi cheez se milta hai.
        """
        bc = self._cell("barcode", row)
        bc.wait_for(state="visible", timeout=10000)
        safety.guarded_click(bc, f"grid.barcode[{row}]")
        safety.safe_clear(bc, self.page)
        bc.type(str(barcode), delay=40)
        bc.press("Enter")
        self.bp.settle()
        self.clear_popups()
        return self._fill_line(row, qty, rate, discount)

    def add_by_name(self, name: str, qty: float = 1,
                    rate: float | None = None,
                    discount: float | None = None, row: int = 0):
        """
        Naam se item jodo -- item window kholkar.
        Barcode ho to add_by_barcode behtar hai.
        """
        bc = self._cell("barcode", row)
        bc.wait_for(state="visible", timeout=10000)
        safety.guarded_click(bc, f"grid.barcode[{row}]")
        bc.press("Enter")                       # khali barcode -> item window
        self._cell("item", row).press("Enter")
        self.bp.settle()

        box = self.page.locator("#searchItems").first
        box.wait_for(state="visible", timeout=8000)
        safety.safe_clear(box, self.page)
        box.type(name, delay=50)
        self.bp.settle()

        prod = self.page.locator('[col-id="Product"]').filter(has_text=name).first
        prod.wait_for(state="visible", timeout=8000)
        prod.dblclick()
        self.bp.settle()
        self.clear_popups()
        return self._fill_line(row, qty, rate, discount)

    def pick_batch(self, batch: str):
        """Batch chuno (pharma). Batch window khuli ho tab."""
        row = self.page.locator('[col-id="batchName"]').filter(has_text=batch).first
        row.wait_for(state="visible", timeout=8000)
        safety.guarded_click(row, f"grid.batch:{batch}", timeout=5000)
        self.bp.settle()
        return self

    def _fill_line(self, row: int, qty, rate, discount):
        """
        Line ke baaki field bharo -- SIRF wo jo maujood hain.

        Har trade me alag column hote hain: kahin discount2 hai kahin nahi,
        kahin volume discount hai kahin nahi. Isliye pehle dekho, phir bharo.
        Jo nahi hai use chhodna galti nahi hai.
        """
        def put(field, value):
            if not ag_grid.cell_exists(self.page, field, row):
                return False
            el = self._cell(field, row)
            if value is not None:
                safety.guarded_click(el, f"grid.{field}[{row}]")
                safety.safe_clear(el, self.page)
                el.type(str(value), delay=40)
            el.press("Enter")
            self.page.wait_for_timeout(250)
            return True

        put("qty", qty)
        put("rate", rate)
        put("discount", discount)
        # ye sirf kuch trade me hote hain -- na hon to koi baat nahi
        for extra in ("discount2", "vol_disc", "vol_disc2"):
            put(extra, None)

        self.bp.settle()
        self.clear_popups()
        return self

    def add_item(self, name: str, qty: float = 1, rate: float | None = None,
                 row: int = 0, discount: float | None = None):
        """
        Purana naam -- chalta rahega.
        Number-jaisa hai to barcode maan lete hain, warna naam.
        discount is optional (Test Studio writes "item | qty | rate | discount").
        """
        if str(name).strip().isdigit():
            return self.add_by_barcode(str(name).strip(), qty, rate, discount, row=row)
        return self.add_by_name(name, qty, rate, discount, row=row)


class SaleReturnPage(SaleBillPage):
    SCREEN = "sale_return"
    TITLE = "Sale Return"


class PurchaseBillPage(SaleBillPage):
    SCREEN = "purchase_bill"
    TITLE = "Purchase Bill"
