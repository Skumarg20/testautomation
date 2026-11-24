"""The signed-in user's rights on one menu entry, as the app itself reads them: the login answer keeps the
role's menu in `LoggedInUserInfo.UserLoginData.menuData`, one entry per screen with `menutext`, `pageurl`
and 0/1 flags `IsView`, `IsExport`, `IsPrint` (Globals/global.ts:13150-13180; read by
importexport.component.ts:538-550). A screen missing from the menu is a screen the role cannot open.
"""

from dataclasses import dataclass

from playwright.sync_api import Page

MENU_ENTRY_SCRIPT = """
(menuText) => {
    const info = JSON.parse(localStorage.getItem('{"key":"LoggedInUserInfo","session":"mb-session"}'));
    const menu = (info && info.UserLoginData && info.UserLoginData.menuData) || [];
    const entry = menu.find((item) => item.menutext === menuText);
    return entry ? {view: entry.IsView, export: entry.IsExport} : null;
}
"""


@dataclass(frozen=True)
class MenuRights:
    can_view: bool
    can_export: bool


NO_RIGHTS = MenuRights(can_view=False, can_export=False)


def menu_rights(page: Page, menu_text: str) -> MenuRights:
    """Call on a page that has finished logging in (the dashboard)."""
    entry = page.evaluate(MENU_ENTRY_SCRIPT, menu_text)
    if entry is None:
        return NO_RIGHTS
    return MenuRights(can_view=entry["view"] == 1, can_export=entry["export"] == 1)
