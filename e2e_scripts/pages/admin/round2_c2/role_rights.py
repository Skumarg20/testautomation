"""Reading a role's rights from Role Configurations, and what a sale bill list offers a limited login.

The expected rights come from the Roles tab (User List > Roles > Edit/F3 of the role), which is independent of
the sale list: the row of the Sale menu named like "Bill" has checkboxes Full, Create, Edit, Delete,
Export, in
this order (pages/admin/role_configuration.py `expect_every_right_checked`). The sale list hides Delete and
Edit
for a role without IsDelete / IsEdit
(Component/Transaction/InverntoryTransaction/processout.list.component.ts:
1106-1110). Part C2 owns this module.
"""

import re
from enum import Enum

from playwright.sync_api import Locator, Page, expect

from pages.admin.role_configuration import RoleConfiguration
from pages.admin.user_master_page import UserMasterPage
from pages.base_page import BasePage
from pages.sale.documents.bill import SaleBillDocument
from pages.sale.documents.screen import DocumentScreen

DIALOG_TIMEOUT_MS = 30_000


class RightColumn(Enum):
    FULL = 0
    CREATE = 1
    EDIT = 2
    DELETE = 3
    EXPORT = 4


class RoleRights(BasePage):
    def granted(self, role: str, menu: str, row_name: re.Pattern[str]) -> dict[RightColumn, bool]:
        """Opens the role, reads the checkboxes of the first row of `menu` matching `row_name`, closes it."""
        users = UserMasterPage(self.page)
        users.open_roles()
        configuration = users.edit_role(role)
        configuration.expect_open()
        dialog = self.page.get_by_role("dialog").filter(
            has=self.page.get_by_role("heading", name="Role Configurations")
        )
        dialog.get_by_role("link", name=menu, exact=True).click()
        boxes = dialog.get_by_role("row", name=row_name).first.get_by_role("checkbox")
        expect(boxes.first).to_be_visible(timeout=DIALOG_TIMEOUT_MS)
        result = {
            column: self._checked(boxes, column) for column in RightColumn if column.value < boxes.count()
        }
        RoleConfiguration(self.page).close()
        return result

    @staticmethod
    def _checked(boxes: Locator, column: RightColumn) -> bool:
        return boxes.nth(column.value).is_checked()


class SaleListActions(BasePage):
    """The first bill row of the sale list: which actions the login is offered."""

    def row_actions(self) -> list[str]:
        row = self.page.locator('[ref="eBodyContainer"] .ag-row').first
        expect(row).to_be_visible(timeout=DIALOG_TIMEOUT_MS)
        row.locator('button[data-toggle="dropdown"]').click()
        items = self.page.locator(".dropdown-menu.show .dropdown-item")
        return [text.strip() for text in items.all_inner_texts()]

    def has_edit_button(self) -> bool:
        row = self.page.locator('[ref="eBodyContainer"] .ag-row').first
        return row.locator("button.mksBtn.edit").count() > 0


def open_sale_list(page: Page, search: str) -> None:
    screen = DocumentScreen(page)
    screen.open_menu(SaleBillDocument.menu)
    screen.search_list(search)
