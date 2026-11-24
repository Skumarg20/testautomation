"""What every sale screen shares: loader, toasts, dialogs, side menu and list-screen actions."""

import re
from typing import Literal

from playwright.sync_api import Locator, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.components.app_texts import LIST_SEARCH_BOX

ToastKind = Literal["success", "error", "warning"]

LOADER_APPEAR_MS = 3_000
LOADER_GONE_MS = 90_000
TOAST_TIMEOUT_MS = 15_000
DIALOG_WAIT_MS = 2_000
ROW_TIMEOUT_MS = 90_000
MENU_EXPAND_ATTEMPTS = 3
MENU_EXPAND_LOOKUP_MS = 3_000
CHALLAN_CHOICE_WAIT_MS = 3_000
DISMISS_LOOKUP_MS = 1_000
RESTORED_FORM_WAIT_MS = 1_000
ROWS_TIMEOUT_MS = 20_000
TICKED_LOOKUP_MS = 2_000

# One shared wait-or-false helper; the sale pages know it by this name.
is_shown_within = appears_within


def tick_every_row(items: Locator) -> None:
    """Ticks every row of an item list with its select-all box, unless the app drew them ticked already.

    The ticked state is read only once the rows are drawn: a box clicked before then unticks every row.
    """
    expect(items.locator(".ag-row").first).to_be_visible(timeout=ROWS_TIMEOUT_MS)
    everything = items.locator(".ag-header-select-all")
    if not is_shown_within(everything.locator(".ag-checkbox-checked"), TICKED_LOOKUP_MS):
        everything.locator(".ag-icon").click()


def exact_text(value: str) -> re.Pattern[str]:
    """Whole-text, case-insensitive match; the app lists codes and names in mixed case.

    Playwright writes a regex into its selector without escaping `/`, so "Create/F2" must carry `\\/`.
    """
    escaped = re.escape(value).replace("/", r"\/")
    return re.compile(rf"^\s*{escaped}\s*$", re.IGNORECASE)


class DocumentScreen(BasePage):
    def wait_for_loader(self) -> None:
        # The app's busy spinner is an svg circle that only has an id.
        loader = self.page.locator('circle[id="Ellipse 363"]')
        if is_shown_within(loader, LOADER_APPEAR_MS):
            expect(loader).to_be_hidden(timeout=LOADER_GONE_MS)

    def expect_toast(self, kind: ToastKind, timeout_ms: int = TOAST_TIMEOUT_MS) -> None:
        toast = self.page.locator(f"notifier-notification.notifier__notification--{kind}")
        expect(toast.first).to_be_visible(timeout=timeout_ms)
        self._dismiss(toast)

    def press_button(self, name: str) -> None:
        self._button(name).click()

    def confirm_yes(self) -> None:
        self.press_button("Yes")

    def confirm_if_asked(self) -> None:
        if is_shown_within(self.active_dialog, DIALOG_WAIT_MS):
            self.confirm_yes()

    @property
    def active_dialog(self) -> Locator:
        return self.page.locator("div.modal-new.active")

    def open_menu(self, path: tuple[str, ...]) -> None:
        *parents, leaf = path
        for name in parents:
            self._expand(name)
        self._click_until_shown(parents, leaf)
        self.confirm_if_asked()
        self._leave_restored_form()
        self.wait_for_loader()

    def search_list(self, unique_id: str) -> None:
        box = self.page.locator(LIST_SEARCH_BOX).first
        box.press("Control+A")
        box.press("Backspace")
        box.press_sequentially(unique_id)
        self.wait_for_loader()

    def filter_list_this_week(self) -> None:
        self.page.locator("button.default-btn.dropdown-toggle").click()
        self.page.get_by_text("This Week", exact=True).click()
        self.wait_for_loader()

    def row_action(self, unique_id: str, action: str) -> None:
        row = self.list_row(unique_id)
        row.locator('button[data-toggle="dropdown"]').click()
        row.get_by_role("link", name=re.compile(re.escape(action))).click()

    def list_row(self, unique_id: str) -> Locator:
        row = self.page.get_by_role("row").filter(has=self.page.get_by_text(unique_id, exact=True))
        expect(row.first).to_be_visible(timeout=ROW_TIMEOUT_MS)
        return row.first

    def delete_listed_record(self, unique_id: str) -> None:
        self.filter_list_this_week()
        self.search_list(unique_id)
        self.row_action(unique_id, "Delete")
        self.wait_for_loader()
        self._confirm_deletion(unique_id)
        self.expect_toast("success", ROW_TIMEOUT_MS)

    def delete_after_conversion(self, unique_id: str) -> None:
        """A converted document cannot be deleted; the app answers with a warning."""
        self.filter_list_this_week()
        self.search_list(unique_id)
        self.row_action(unique_id, "Delete")
        self.wait_for_loader()
        self.expect_toast("warning")

    def close_print_window_if_shown(self) -> None:
        print_window = self.page.locator("#billDetailForm")
        if is_shown_within(print_window, DIALOG_WAIT_MS):
            self.page.locator(".modal-header").get_by_text("×").first.click()

    def _confirm_deletion(self, unique_id: str) -> None:
        if is_shown_within(self.page.locator("delete-load-challan-window"), CHALLAN_CHOICE_WAIT_MS):
            self.press_button("Re-Convert into Challan")
        else:
            expect(self.page.locator("i", has_text=unique_id)).to_be_visible(timeout=ROW_TIMEOUT_MS)
        self.confirm_if_asked()

    def _dismiss(self, toast: Locator) -> None:
        dismiss = self.page.get_by_title("dismiss")
        if is_shown_within(dismiss, DISMISS_LOOKUP_MS):
            dismiss.first.click()
        try:
            toast.first.wait_for(state="hidden", timeout=TOAST_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            return  # A toast that outlives the wait is harmless; the next check names its own kind.

    def _click_until_shown(self, parents: list[str], leaf: str) -> None:
        """The group's "collapsed" class does not always say whether it is open (app V. 4.3.599.b left Sale
        shut, OA-034 on 2026-10-13), so the last group is clicked again until the target link shows."""
        target = self._menu_link(leaf)
        for _ in range(MENU_EXPAND_ATTEMPTS):
            if is_shown_within(target, MENU_EXPAND_LOOKUP_MS) or not parents:
                break
            self._menu_link(parents[-1]).click()
        target.click()

    def _expand(self, name: str) -> None:
        link = self._menu_link(name)
        if "collapsed" in (link.get_attribute("class") or ""):
            link.click()

    def _menu_link(self, name: str) -> Locator:
        """The side-menu link is named by its icon alt text plus its label, for example "Sale Sale"."""
        label = re.escape(name)
        return self.page.get_by_role("link", name=re.compile(rf"^{label}( {label})?$")).first

    def _leave_restored_form(self) -> None:
        """The router sometimes reopens a form that was open earlier; leave it for the list."""
        if is_shown_within(self.page.locator(".frameModal"), RESTORED_FORM_WAIT_MS):
            self.page.keyboard.press("Escape")
            self.confirm_if_asked()

    def _button(self, name: str) -> Locator:
        return self.page.get_by_role("button", name=exact_text(name)).first
