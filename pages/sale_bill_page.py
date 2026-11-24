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

    # Grid column ids per field (the first that exists in this trade's grid wins).
    _COLS = {"qty": ("unitToEnteredValue", "quantity"), "rate": ("salePurchaseRate",), "discount": ("discount1",)}

    @staticmethod
    def _same_number(got, want) -> bool:
        import re as _re
        try:
            g = float(_re.sub(r"[^\d.\-]", "", str(got or "")) or "nan")
            return abs(g - float(str(want).replace(",", ""))) < 1e-9
        except ValueError:
            return str(got).strip() == str(want).strip()

    def _away_from_menu(self):
        """The side menu expands under the mouse and covers the grid's first columns: park the mouse on the form."""
        try:
            self.page.mouse.move(900, 300)
            self.page.wait_for_timeout(250)
        except Exception:  # noqa: BLE001
            pass

    def _row_cell(self, row: int, col: str):
        return self.page.locator(f'[role="row"][row-index="{row}"] [col-id="{col}"]')

    def _visible(self, loc) -> bool:
        try:
            return loc.count() > 0 and loc.first.is_visible()
        except Exception:  # noqa: BLE001
            return False

    def _open_item_window(self, row: int) -> None:
        """Open "Select Item" for a grid line: Enter on an empty barcode cell, else Space on the product cell."""
        self._away_from_menu()
        box = self.page.locator("input#searchItems")
        if self._visible(box):
            return
        bc = self._cell("barcode", row)
        if self._visible(bc):
            safety.guarded_click(bc.first, f"grid.barcode[{row}]", inside_modal=True)
            bc.first.press("Enter")
        else:
            for col in ("itemLinkID", "Product", "itemName"):
                cell = self._row_cell(row, col)
                if self._visible(cell):
                    safety.guarded_click(cell.first, f"grid.product[{row}]", inside_modal=True)
                    break
            self.page.keyboard.press("Space")
        for _ in range(3):
            try:
                box.first.wait_for(state="visible", timeout=4000)
                return
            except Exception:  # noqa: BLE001
                self.page.keyboard.press("Enter")
        raise FormNotOpen("The Select Item window did not open for this line.")

    def _after_pick(self) -> None:
        """A batch trade opens "Select Batch" after the item: take the first (FIFO) batch, like Enter does for a user."""
        self.page.wait_for_timeout(800)
        for _ in range(3):
            modal = self.page.locator("ngb-modal-window, .modal.show")
            try:
                if not (modal.count() and modal.last.is_visible()):
                    return
                text = (modal.last.inner_text(timeout=2000) or "").lower()
            except Exception:  # noqa: BLE001
                return
            is_batch = "batch" in text or modal.last.locator('[col-id="batchName"], [col-id="BatchName"]').count() > 0
            if not is_batch:
                return
            self.page.keyboard.press("Enter")            # first batch, as a user's Enter does
            self.page.wait_for_timeout(900)

    def _edit_cell(self, row: int, field: str, value) -> bool:
        """Type a value into a grid cell: use its open editor, else click the cell to open it. False if no such column."""
        if value is None:
            return False
        inp = None
        for col in self._COLS[field]:
            loc = self.page.locator(f"#txt-{col}-{row}")
            if self._visible(loc):
                inp = loc.first
                break
        if inp is None:
            for col in self._COLS[field]:
                cell = self._row_cell(row, col)
                if self._visible(cell):
                    safety.guarded_click(cell.first, f"grid.{field}[{row}]", inside_modal=True)
                    self.page.wait_for_timeout(400)
                    loc = self.page.locator(f"#txt-{col}-{row}")
                    if self._visible(loc):
                        inp = loc.first
                        break
        if inp is None:
            return False
        try:
            inp.evaluate("e => { e.focus(); if (e.select) e.select(); }")   # replace the 0.00 the cell starts with
            self.page.wait_for_timeout(150)
            inp.evaluate("e => { if (e.select) e.select(); }")             # Angular fills the editor late
        except Exception:  # noqa: BLE001
            inp.press("Control+a")
        inp.type(str(value), delay=40)
        # The editor may get its "0.00" after the select: typing "1" then gave "10.00" (pharma replay). Check what
        # the cell holds and, when it is not the value, empty it key by key and type again.
        try:
            got = inp.input_value()
            if not self._same_number(got, value):
                inp.press("End")
                for _ in range(len(got or "") + 2):
                    inp.press("Backspace")
                inp.type(str(value), delay=40)
        except Exception:  # noqa: BLE001
            pass
        inp.press("Enter")
        self.page.wait_for_timeout(350)
        return True

    def add_by_barcode(self, barcode: str, qty: float = 1,
                       rate: float | None = None,
                       discount: float | None = None, row: int = 0):
        """Barcode se item jodo -- sabse bharosemand tareeka (ek barcode, ek item)."""
        self._away_from_menu()
        bc = self._cell("barcode", row)
        bc.first.wait_for(state="visible", timeout=10000)
        safety.guarded_click(bc.first, f"grid.barcode[{row}]", inside_modal=True)
        safety.safe_clear(bc.first, self.page)
        bc.first.type(str(barcode), delay=40)
        bc.first.press("Enter")
        self.bp.settle()
        self._after_pick()
        return self._fill_line(row, qty, rate, discount)

    def add_by_name(self, name: str, qty: float = 1,
                    rate: float | None = None,
                    discount: float | None = None, row: int = 0):
        """
        Naam se item jodo -- "Select Item" window kholkar, naam search karke, row chunkar.

        Live-app checks (artifacts/verify) showed the old way failing: it needed a barcode column (not in every
        trade), closed the batch window with clear_popups, and the expanded side menu covered the grid.
        """
        self._open_item_window(row)
        box = self.page.locator("input#searchItems").first
        safety.guarded_click(box, "item.search", inside_modal=True)
        safety.safe_clear(box, self.page)
        box.type(name, delay=50)
        self.bp.settle()
        hit = self.page.locator("ngb-modal-window [col-id='Product'], .modal.show [col-id='Product']").filter(has_text=name)
        hit.first.wait_for(state="visible", timeout=10000)
        safety.guarded_click(hit.first, f"item.pick:{name}", inside_modal=True)
        self.page.wait_for_timeout(500)
        if self._visible(self.page.locator("input#searchItems")):      # a single click only highlighted it
            self.page.keyboard.press("Enter")
        self.bp.settle()
        self._after_pick()
        return self._fill_line(row, qty, rate, discount)

    def pick_batch(self, batch: str):
        """Batch chuno (pharma). Batch window khuli ho tab."""
        row = self.page.locator('[col-id="batchName"]').filter(has_text=batch).first
        row.wait_for(state="visible", timeout=8000)
        safety.guarded_click(row, f"grid.batch:{batch}", timeout=5000, inside_modal=True)
        self.bp.settle()
        return self

    def _fill_line(self, row: int, qty, rate, discount):
        """
        Line ke baaki field bharo -- SIRF wo jo maujood hain (har trade me alag column hote hain).
        Qty is typed into the cell the cursor lands on after the item (or batch) is picked.
        """
        if qty is not None and not self._edit_cell(row, "qty", qty):
            raise FormNotOpen("The quantity cell of the line did not open.")
        self._edit_cell(row, "rate", rate)
        self._edit_cell(row, "discount", discount)
        self.bp.settle()
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
