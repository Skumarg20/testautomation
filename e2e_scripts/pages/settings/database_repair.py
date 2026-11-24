from pages.base_page import BasePage

PLEASE_WAIT_APPEAR_MS = 20_000
REPAIR_FINISH_MS = 600_000


class DatabaseRepair(BasePage):
    def repair(self) -> None:
        self.page.get_by_title("Utilities & Tools").click()
        self.page.wait_for_load_state("load")
        self.page.get_by_role("link", name="Repair DataBase").click()
        self.page.locator("#txtYes").click()
        busy = self.page.get_by_text("Please wait", exact=False)
        busy.wait_for(state="visible", timeout=PLEASE_WAIT_APPEAR_MS)
        busy.wait_for(state="hidden", timeout=REPAIR_FINISH_MS)
