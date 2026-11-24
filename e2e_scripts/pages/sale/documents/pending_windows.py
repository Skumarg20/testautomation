"""The "Pending Challans / Orders / Quotation" windows that open after choosing a party."""

from dataclasses import dataclass
from typing import Literal

from playwright.sync_api import Locator, expect

from pages.base_page import BasePage
from pages.sale.documents.screen import DocumentScreen, is_shown_within, tick_every_row

Kind = Literal["Challan", "Order", "Quote"]
WINDOW_TITLES: dict[Kind, str] = {
    "Challan": "Pending Challans",
    "Order": "Pending Orders",
    "Quote": "Pending Quotation",
}
APPEARANCE_ORDER: tuple[Kind, ...] = ("Challan", "Order", "Quote")
APPEAR_WAIT_MS = 2_000
LEFT_OPEN_LOOKUP_MS = 500
ITEM_WINDOW_TIMEOUT_MS = 20_000


@dataclass(frozen=True)
class Templates:
    """The numbers of earlier documents a new document is built from; empty means none."""

    quote: str = ""
    order: str = ""
    challan: str = ""

    def number_for(self, kind: Kind) -> str:
        return {"Challan": self.challan, "Order": self.order, "Quote": self.quote}[kind]

    @property
    def is_empty(self) -> bool:
        return not (self.quote or self.order or self.challan)


NO_TEMPLATES = Templates()


class PendingWindows(BasePage):
    def resolve(self, templates: Templates) -> None:
        """Take the wanted document from each window that opened and close the others."""
        for kind in APPEARANCE_ORDER:
            if not is_shown_within(self._window(kind), APPEAR_WAIT_MS):
                continue
            number = templates.number_for(kind)
            if number:
                self._pull_from(kind, number)
            else:
                self._close(kind)

    def close_all(self) -> None:
        for kind in APPEARANCE_ORDER:
            if is_shown_within(self._window(kind), LEFT_OPEN_LOOKUP_MS):
                self._close(kind)

    def _pull_from(self, kind: Kind, number: str) -> None:
        window = self._window(kind)
        window.locator("#SearchBox").fill(number)
        # Exact number, inside this window only: "12" must not tick "112" or a row of another grid.
        row = window.locator(".ag-row-position-absolute").filter(
            has=self.page.get_by_text(number, exact=True)
        )
        row.locator(".ag-icon-checkbox-unchecked").first.click()
        window.get_by_role("button", name="Save").click()
        expect(window).to_be_hidden()
        self._select_every_item()

    def _select_every_item(self) -> None:
        items = self.page.locator("challanorder-item")
        expect(items).to_be_visible(timeout=ITEM_WINDOW_TIMEOUT_MS)
        tick_every_row(items)
        items.get_by_role("button", name="Save").click()
        DocumentScreen(self.page).confirm_if_asked()
        expect(items).to_be_hidden()

    def _close(self, kind: Kind) -> None:
        self._window(kind).get_by_text("×").first.click()

    def _window(self, kind: Kind) -> Locator:
        # `pending-challan` is the app's own element; its title tells the three windows apart.
        return self.page.locator("pending-challan").filter(has_text=WINDOW_TITLES[kind])
