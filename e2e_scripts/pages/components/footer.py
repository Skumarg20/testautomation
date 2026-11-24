from playwright.sync_api import Locator

from pages.base_page import BasePage


class Footer(BasePage):
    @property
    def save_button(self) -> Locator:
        return self.page.locator("span").get_by_text("Save", exact=True)

    def save(self) -> None:
        self.save_button.click()
