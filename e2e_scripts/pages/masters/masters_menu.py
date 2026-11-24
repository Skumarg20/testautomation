"""The sidebar entries of Master > Accounts Master: the Group list and the Ledger list."""

from pages.accounting.accounting_menu import MASTER_GROUP, AccountingMenu

ACCOUNT_GROUP_PATH = ("Accounts Master", "Group")


class MastersMenu(AccountingMenu):
    def open_account_group_list(self) -> None:
        self._open(MASTER_GROUP, ACCOUNT_GROUP_PATH)
