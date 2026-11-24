"""The "Template Studio" dialog that Customise opens on a print template (specs/template-designer.md).

Live 2026-10-09: tabs General, Company, Party, Item Table, Footer; a live preview of a sample bill under the
form; a "Save as Template" checkbox with the template name box and a Save button at the bottom. The name box
is the last textbox of the dialog. Saving answers with a toast ("Template Saved Successfully" or
"Template Name Required").
"""

import re

from playwright.sync_api import Locator, expect

from pages.accounting.toasts import Toasts
from pages.base_page import BasePage

STUDIO_TITLE = "Template Studio"
SAVED_MESSAGE = re.compile("template saved successfully", re.IGNORECASE)
STUDIO_TIMEOUT_MS = 30_000
ACTIVE_TAB = re.compile(r"\bactive\b")


class TemplateStudio(BasePage):
    def expect_open(self) -> None:
        expect(self._dialog).to_be_visible(timeout=STUDIO_TIMEOUT_MS)

    def enter_title(self, title: str) -> None:
        self._open_tab("General")
        # Why typed: fill() sets the value without the key events the Studio listens to, so the title was
        # neither previewed nor saved (probe 2026-10-15).
        self._title_box.press("Control+A")
        self._title_box.press_sequentially(title)
        self._title_box.press("Tab")

    def expect_title(self, title: str) -> None:
        self._open_tab("General")
        expect(self._title_box).to_have_value(title)

    def show_item_column(self, column: str) -> None:
        """Ticks the Item Table checkbox of a column, `column` being its field id (for example `free`)."""
        self._open_tab("Item Table")
        self._item_column_checkbox(column).check()

    def expect_item_column_ticked(self, column: str) -> None:
        self._open_tab("Item Table")
        expect(self._item_column_checkbox(column)).to_be_checked()

    def expect_preview_column(self, header: str) -> None:
        expect(self._dialog.get_by_role("columnheader", name=header, exact=True)).to_be_visible()

    def expect_no_preview_column(self, header: str) -> None:
        expect(self._dialog.get_by_role("columnheader", name=header, exact=True)).to_have_count(0)

    def save_as_template(self, name: str) -> None:
        self._dialog.get_by_role("checkbox", name="Save as Template").check()
        self._name_box.fill(name)
        self._dialog.get_by_role("button", name="Save", exact=True).click()

    def expect_saved(self) -> None:
        Toasts(self.page).expect_success_saying(SAVED_MESSAGE)
        expect(self._dialog).to_be_hidden(timeout=STUDIO_TIMEOUT_MS)

    def expect_refused_saying(self, message: re.Pattern[str]) -> None:
        Toasts(self.page).expect_any_saying(message)
        expect(self._dialog).to_be_visible()

    def close(self) -> None:
        self._dialog.get_by_role("button", name="Close").first.click()
        expect(self._dialog).to_be_hidden(timeout=STUDIO_TIMEOUT_MS)

    @property
    def _dialog(self) -> Locator:
        return self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name=STUDIO_TITLE, exact=True)
        )

    @property
    def _title_box(self) -> Locator:
        return self._dialog.get_by_role("tabpanel").get_by_role("textbox").first

    @property
    def _name_box(self) -> Locator:
        return self._dialog.get_by_role("textbox").last

    def _open_tab(self, name: str) -> None:
        tab = self._dialog.get_by_role("tab", name=name, exact=True)
        tab.click()
        # aria-selected stays "false" on the open tab (seen 2026-10-10); the `active` class is reliable.
        expect(tab).to_have_class(ACTIVE_TAB)

    def _item_column_checkbox(self, column: str) -> Locator:
        # Why CSS: the column checkboxes have no label; their id is the field id plus "-control".
        return self._dialog.locator(f"#{column}-control")
