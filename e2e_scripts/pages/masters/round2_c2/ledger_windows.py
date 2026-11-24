"""Boxes and windows of the Create/Modify Party form that round 2 needs: e-mail, Credit Limit, Other Info.

Source (newmarg-webangular20/src/app):
- e-mail box `#txtEmail1`: UI/Master/Ledger/createledger.component.html:1048 and :1767 (the form draws it
in one
  of two layouts, so the visible one is used).
- Credit Limit button `#btnLimit`: createledger.component.html:2062-2070. It is drawn only for a super
admin or a
  user with the right AllowToManagePartyCreditLimits (Component/Master/Ledger/createledger.component.ts:325).
  Its window: UI/Master/Ledger/sub.window.limit.html (`#txtCreditLimit`, `#ddlCreditLimitAction`).
- Other Info button `#btnOthers` (createledger.component.html:2099) and its window
sub.window.other.html:163-186
  (`#ddlStatus` Continue / Discontinue, `#ddlHide` Visibility).
The option labels come from the server (`drpList.LedgerStatus`, `drpList.Visibility`,
`drpList.CreditLimitActionData`), so they are matched by their words, not by position.
"""

import re
from decimal import Decimal
from enum import Enum

from playwright.sync_api import Locator, expect

from pages.accounting.waiting import appears_within
from pages.base_page import BasePage
from pages.sale.manual.option_settings import index_of_option

WINDOW_TIMEOUT_MS = 15_000
BUTTON_LOOKUP_MS = 5_000
APPLY_BUTTON = re.compile(r"(Save|Update)")


class CreditLimitAction(Enum):
    """The three actions of `#ddlCreditLimitAction`; the words are those the server's own check uses
    (margbookscoreapi margerpdal/SaleChallanBill.cs:5022-5024: 1 Only Indicate, 2 Follow Strictly, else
    Stop Billing)."""

    ONLY_INDICATE = "Only Indicate"
    FOLLOW_STRICTLY = "Follow Strictly"
    STOP_BILLING = "Stop Billing"


class CreditLimitNotOfferedError(AssertionError):
    def __init__(self) -> None:
        super().__init__(
            "The party form shows no Credit Limit button: the login is neither a super admin nor allowed to "
            "manage party credit limits (createledger.component.ts:325)"
        )


class LedgerExtras(BasePage):
    """Works on the party form that is open."""

    def type_email(self, email: str) -> None:
        self.page.locator("#txtEmail1").locator("visible=true").first.fill(email)

    def set_credit_limit(self, limit: Decimal, action: CreditLimitAction) -> None:
        button = self.page.locator("#btnLimit")
        if not appears_within(button, BUTTON_LOOKUP_MS):
            raise CreditLimitNotOfferedError
        button.click()
        window = self._window_holding("#txtCreditLimit")
        window.locator("#txtCreditLimit").fill(format(limit, "f"))
        self._choose(window.locator("#ddlCreditLimitAction"), "Credit Limit Action", action.value)
        self._apply(window)

    def discontinue(self) -> None:
        """Other Info > Status = Discontinue: Helper.services.ts:11728-11745 keeps only Continue ledgers in a
        transaction's party list."""
        self._set_other_info("#ddlStatus", "Status", "discontinue")

    def hide(self) -> None:
        """Other Info > Visibility = Hide (shown in a bill only to a user with the visibility power)."""
        self._set_other_info("#ddlHide", "Visibility", "hide")

    def _set_other_info(self, select_id: str, label: str, wanted: str) -> None:
        self.page.locator("#btnOthers").click()
        window = self._window_holding(select_id)
        self._choose(window.locator(select_id), label, wanted)
        self._apply(window)

    def _window_holding(self, selector: str) -> Locator:
        window = self.page.locator("ngb-modal-window").filter(has=self.page.locator(selector))
        expect(window).to_be_visible(timeout=WINDOW_TIMEOUT_MS)
        return window

    @staticmethod
    def _choose(select: Locator, label: str, wanted: str) -> None:
        offered = [text.strip() for text in select.locator("option").all_inner_texts()]
        select.select_option(index=index_of_option(label, wanted, offered))

    @staticmethod
    def _apply(window: Locator) -> None:
        window.get_by_role("button", name=APPLY_BUTTON).first.click()
        expect(window).to_be_hidden(timeout=WINDOW_TIMEOUT_MS)
