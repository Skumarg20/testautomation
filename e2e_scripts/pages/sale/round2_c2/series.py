"""Control Room > Multi Series > Sale Bill: create and delete a bill series of the test's own.

Source: UtililityComponent/DynamicForm/multiseries.component.html (tree of transaction types on the left,
form on
the right: Series Name `#txtSeries`, Max. Length `#txtMaxL`, Prefix `#txtPrefix`, Criteria `#drpDL`, Save
`#btnPrimary`, Delete `#btnDelete` for a saved series). The option "Multi Series" must be Yes (KB "How to
enable
Multi Bill Series"); a series can be deleted only while it has no bills. The bill then opens "Select Series"
(Component/Transaction/multi.series.selection.ts). Part C2 owns this module.
"""

import re

from playwright.sync_api import Locator, Page, expect

from pages.base_page import BasePage
from pages.components.confirm_dialog import ConfirmDialog
from pages.settings.control_room import ControlRoom

MULTI_SERIES = "Multi Series"
FORM_TIMEOUT_MS = 30_000
MAX_LENGTH = "6"


class MultiSeriesConfig(BasePage):
    def open(self) -> None:
        room = ControlRoom(self.page)
        self.page.wait_for_load_state("load")
        room.open_button.click()
        room.configure_button.click()
        room.search.click()
        room.search.press_sequentially(MULTI_SERIES)
        row = self.page.locator(".row.m-0", has_text=MULTI_SERIES).first
        row.get_by_role("button", name="Configure").click()
        self.page.get_by_text("Sale Bill", exact=True).first.click()

    def criteria_options(self) -> list[str]:
        self._start_new()
        return [text.strip() for text in self.page.locator("#drpDL").locator("option").all_inner_texts()]

    def create(self, name: str, criteria_index: int) -> None:
        self._start_new()
        self.page.locator("#txtSeries").fill(name)
        self.page.locator("#txtMaxL").fill(MAX_LENGTH)
        self.page.locator("#drpDL").select_option(index=criteria_index)
        self.page.locator("#btnPrimary").click()

    def delete(self, name: str) -> None:
        self.page.get_by_text(name, exact=True).first.click()
        self.page.locator("#btnDelete").click()
        ConfirmDialog(self.page).answer_yes()

    def close(self) -> None:
        self.page.keyboard.press("Escape")

    def _start_new(self) -> None:
        self.page.keyboard.press("F2")
        expect(self.page.locator("#txtSeries")).to_be_visible(timeout=FORM_TIMEOUT_MS)


def series_cell(page: Page, name: str) -> Locator:
    """A series in the Select Series window of a new bill."""
    return page.get_by_role("gridcell", name=re.compile(re.escape(name)))
