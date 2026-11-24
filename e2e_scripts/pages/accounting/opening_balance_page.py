"""Master > Opening Balance > Ledger: create a ledger with an opening balance, change it, read it, delete it.

The page lists every ledger with its opening balance; "Create/F2" and "Edit/F3" open the same ledger
form ("Create Party" / "Modify Party") that holds the "Opening Balance" amount and a Dr/Cr select.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from playwright.sync_api import Locator, expect

from pages.accounting.list_screen import ListScreen
from pages.accounting.loader import Loader
from pages.accounting.toasts import Toasts
from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.components.confirm_dialog import ConfirmDialog
from test_data.money import parse_amount

Side = Literal["Dr", "Cr"]
BalancingMethod = Literal["Bill By Bill", "On Account"]
PARTY_GROUP = "Sundry Debtors"
PARTY_STATION = "Others"
PARTY_MOBILE = "9876543210"
SAVED = re.compile(r"Record (saved|updated) successfully", re.IGNORECASE)
BILL_WINDOW_MS = 3_000
SAVE_BUTTON = re.compile(r"^F10 (Save|Update)$")
BALANCE_COLUMN = 2
FORM_TIMEOUT_MS = 30_000
NAVIGATION_TIMEOUT_MS = 90_000


@dataclass(frozen=True)
class OpeningBalance:
    amount: Decimal
    side: Side


@dataclass(frozen=True)
class LedgerSpec:
    """A ledger this test owns. Sundry Debtors ledgers are parties and need a station and a mobile."""

    name: str
    opening: OpeningBalance
    group: str = PARTY_GROUP
    balancing_method: BalancingMethod = "On Account"

    @property
    def is_party(self) -> bool:
        return self.group == PARTY_GROUP


class OpeningBalancePage(BasePage):
    PATH = "/partymaster/opening-ledger"

    def create_ledger(self, ledger: LedgerSpec) -> None:
        self._open_list()
        self.page.get_by_role("button", name="Create/F2", exact=True).click()
        self._form_fields(ledger)
        self._save_form()

    def change_opening(self, name: str, opening: OpeningBalance) -> None:
        self._open_ledger(name)
        self._enter_opening(opening)
        self._save_form()

    def listed_opening(self, name: str) -> OpeningBalance:
        """The opening balance in the list's "₹ Balance" column, for example "1,234.500 Cr"."""
        self._open_list()
        cell = self._row(name).get_by_role("gridcell").nth(BALANCE_COLUMN)
        expect(cell).to_have_text(re.compile(r"\d.*(Dr|Cr)"), timeout=FORM_TIMEOUT_MS)
        return _opening_from_text(cell.inner_text())

    def saved_opening(self, name: str) -> OpeningBalance:
        """The opening balance the ledger form shows when the ledger is opened again."""
        self._open_ledger(name)
        expect(self._amount_input).not_to_have_value("", timeout=FORM_TIMEOUT_MS)
        side = self._side_select.locator("option:checked").inner_text().strip()
        return OpeningBalance(parse_amount(self._amount_input.input_value()), _side(side))

    def delete_ledger(self, name: str) -> None:
        self._open_list()
        self._row(name).get_by_role("button", name="Delete").click()
        ConfirmDialog(self.page).answer_yes()
        # The success toast is short-lived and was missed under load, so the list itself is the proof.
        self._open_list()
        ListScreen(self.page).search(name)
        expect(self._name_cell(name)).to_have_count(0, timeout=FORM_TIMEOUT_MS)

    def _open_list(self) -> None:
        self.goto(self.PATH, NAVIGATION_TIMEOUT_MS)
        Loader(self.page).wait_until_idle()
        expect(self.page.get_by_role("heading", name=re.compile(r"^Opening Balance"))).to_be_visible(
            timeout=FORM_TIMEOUT_MS
        )

    def _open_ledger(self, name: str) -> None:
        self._open_list()
        self._row(name).get_by_role("button", name="Edit/F3").click()
        Loader(self.page).wait_until_idle()
        expect(self.page.locator("#txtlegername")).to_have_value(name, timeout=FORM_TIMEOUT_MS)

    def _row(self, name: str) -> Locator:
        ListScreen(self.page).search(name)
        row = self.page.get_by_role("row").filter(has=self._name_cell(name))
        expect(row).to_have_count(1, timeout=FORM_TIMEOUT_MS)
        return row

    def _name_cell(self, name: str) -> Locator:
        return self.page.get_by_role("gridcell", name=name, exact=True)

    def _form_fields(self, ledger: LedgerSpec) -> None:
        # Why ids: the form labels are not linked to their inputs, so get_by_label finds nothing.
        name_input = self.page.locator("#txtlegername")
        expect(name_input).to_be_visible(timeout=FORM_TIMEOUT_MS)
        name_input.fill(ledger.name)
        if ledger.is_party:
            self._party_fields(ledger)
        else:
            self._choose_from_typeahead(self.page.locator("#drpAccountGroup"), ledger.group)
        self._enter_opening(ledger.opening)

    def _party_fields(self, ledger: LedgerSpec) -> None:
        self._choose_from_typeahead(self.page.locator("#ddlstation"), PARTY_STATION)
        self.page.locator("#txtMobile").fill(PARTY_MOBILE)
        self.page.locator("#ddlBalancingMethod").select_option(label=ledger.balancing_method)

    def _choose_from_typeahead(self, field: Locator, choice: str) -> None:
        field.click()
        field.press("Control+A")
        field.press_sequentially(choice)
        suggestions = self.page.get_by_role("listbox")
        suggestions.get_by_role("option", name=choice, exact=True).first.click()

    def _enter_opening(self, opening: OpeningBalance) -> None:
        self._amount_input.click()
        self._amount_input.press("Control+A")
        self._amount_input.press_sequentially(str(opening.amount))
        self._side_select.select_option(label=opening.side)

    def _save_form(self) -> None:
        self.page.get_by_role("button", name=SAVE_BUTTON).click()
        self._confirm_bill_details()
        Toasts(self.page).expect_success_saying(SAVED)

    def _confirm_bill_details(self) -> None:
        """A Bill By Bill party first opens the bill-wise window (Amount fixed, empty bill grid); its own
        Save returns to the party form, whose Save then finishes the ledger (probe 2026-10-16)."""
        window = self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name="Opening Balance", level=5)
        )
        if appears_within(window, BILL_WINDOW_MS):
            window.get_by_role("button", name=SAVE_BUTTON).click()
            expect(window).to_be_hidden(timeout=FORM_TIMEOUT_MS)
            self.page.get_by_role(
                "button", name=SAVE_BUTTON
            ).click()  # back on the party form, now to save it

    @property
    def _amount_input(self) -> Locator:
        return self.page.locator("#txtOpeningBalance")

    @property
    def _side_select(self) -> Locator:
        return self.page.locator("#ddlIsDebitCredit")


def _opening_from_text(text: str) -> OpeningBalance:
    amount, side = text.split()
    return OpeningBalance(parse_amount(amount), _side(side))


def _side(text: str) -> Side:
    if text == "Dr":
        return "Dr"
    if text == "Cr":
        return "Cr"
    raise ValueError(f'Unknown balance side "{text}", expected Dr or Cr')
