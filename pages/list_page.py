"""
Har LIST screen ke liye ek POM -- Item List, Ledger Master, Store, Salt, HSN...

Ye saare list page ek jaise bane hain: heading, search box, Create/F2,
grid, aur "Total no of ..." label. Isliye ek hi class sabke liye kaafi hai.

Jahan kuch khaas hai (Item, Ledger), wahan iski upar se class banayi hai --
ItemPage, PartyPage. Baaki 15 screens ke liye alag class likhna sirf code
badhata, kuch deta nahi.
"""
from __future__ import annotations

from framework import safety
from framework.base_page import BasePage
from framework.screens import open_screen
from pages.grid import visible_rows, total_count, scroll_all, has_not_found_alert


class ListPage:
    SCREEN = ""
    SEARCH_SEL = 'input[type="search"], input[placeholder="Search here.."]'
    HEADER = ""          # grid ke pehle column ka naam
    TOTAL_LABEL = ""     # "Total no of items" jaisa
    CREATE_TEXT = "Create/F2"

    def __init__(self, bp: BasePage, screen: str | None = None):
        self.bp = bp
        self.page = bp.page
        if screen:
            self.SCREEN = screen

    @classmethod
    def open(cls, bp: BasePage, screen: str | None = None, verbose: bool = False):
        key = screen or cls.SCREEN
        if not open_screen(bp, key, verbose=verbose):
            raise RuntimeError(f"'{key}' khul nahi paya. URL: {bp.page.url}")
        page = cls(bp, screen=key)
        try:
            page.clear_search()
        except Exception:  # noqa: BLE001
            pass
        return page

    # ---- search ----

    def _search_box(self):
        return self.page.locator(self.SEARCH_SEL).first

    def search(self, text: str):
        safety.dismiss_modal(self.page)
        el = self._search_box()
        safety.guarded_click(el, f"{self.SCREEN}.search")
        safety.safe_clear(el, self.page)
        if text:
            el.type(text, delay=50)
        self.bp.settle()
        return self

    def clear_search(self, wait_ms: int = 6000):
        self.search("")
        waited = 0
        while waited < wait_ms and not self.names():
            self.bp.settle(quiet_ms=300, timeout_ms=2000)
            waited += 400
        return self

    def search_check(self, term: str) -> dict:
        """Search chala ya nahi -- filter / jump / not_found / silent."""
        before = self.names()
        self.search(term)
        after = self.names()
        t = term.lower()
        matching = [n for n in after if t in n.lower()]
        alerted, msg = has_not_found_alert(self.page)
        if alerted:
            mode = "not_found"
        elif after and len(matching) == len(after):
            mode = "filter"
        elif not after and before:
            mode = "filter_empty"
        elif after and t in after[0].lower():
            mode = "jump"
        else:
            mode = "silent"
        return {"mode": mode, "works": mode != "silent",
                "before": len(before), "after": len(after),
                "matching": len(matching), "alert": msg}

    # ---- grid ----

    def rows(self) -> list[list[str]]:
        if not self.HEADER:
            raise RuntimeError(
                f"'{self.SCREEN}' ke liye HEADER set nahi hai -- grid ka pehla "
                f"column ka naam chahiye (jaise 'Description').")
        return visible_rows(self.page, self.HEADER)

    def all_rows(self) -> list[list[str]]:
        return scroll_all(self.page, self.HEADER)

    def names(self) -> list[str]:
        try:
            return [r[0] for r in self.rows() if r and r[0]]
        except Exception:  # noqa: BLE001
            return []

    def total(self) -> int | None:
        """Header ka total. DHYAAN: filter par ye NAHI badalta."""
        return total_count(self.page, self.TOTAL_LABEL) if self.TOTAL_LABEL else None

    def has(self, name: str) -> bool:
        return any(name.lower() in n.lower() for n in self.names())

    # ---- create ----

    def open_create(self):
        btn = self.page.get_by_role("button", name=self.CREATE_TEXT).first
        safety.guarded_click(btn, f"{self.SCREEN}.create")
        self.bp.settle()
        safety.dismiss_modal(self.page)
        return self
