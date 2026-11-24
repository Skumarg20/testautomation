"""Utilities & Tools > Other Tools in the side menu, where "DataSync Details" would sit (J35 DS-15).

The menu row "DataSync Details" (`/other/datasyncreport`) has `isactive: 0` (`menumaster.json:5911-5917`,
`AlterMainDB.xml:1319`), so it should not be listed. "Multi Editing" sits in the same sub-menu (KB
`onedrive_processed_data.csv#61d9a9e6`) and proves the sub-menu really opened. DRAFT: not seen live.
"""

from playwright.sync_api import Locator

from pages.purchase.documents.navigation import MENU_TIMEOUT_MS, ModuleMenu

UTILITIES_GROUP = "Utilities & Tools"
OTHER_TOOLS = "Other Tools"
MULTI_EDITING = "Multi Editing"
DATA_SYNC_DETAILS = "DataSync Details"


class OtherToolsMenu(ModuleMenu):
    def open_other_tools(self) -> None:
        self._expand_menu(UTILITIES_GROUP)
        self._expand(self._group(UTILITIES_GROUP))
        parent = self._parent_link(OTHER_TOOLS)
        parent.wait_for(state="visible", timeout=MENU_TIMEOUT_MS)
        self._expand(parent)

    def entry(self, name: str) -> Locator:
        return self._child_link(name)
