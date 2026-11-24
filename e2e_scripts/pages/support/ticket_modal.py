"""The "Create Ticket" / "Update Ticket" modal (`create-ticket.component.html`, `create-ticket.component.ts`).
Locators from the Angular source, not yet checked live.

The three selects and the description carry ids but their labels have no `for`, so they are found by id.
Several footer buttons share `id="submit"`, so buttons are found by role and name instead.
"""

from playwright.sync_api import FilePayload, Locator, Page, expect

from pages.base_page import BasePage

CREATE_TITLE = "Create Ticket"
UPDATE_TITLE = "Update Ticket"
MODAL_TIMEOUT_MS = 30_000
SUGGESTIONS_TITLE = "May be this is useful for you!"
SUGGESTION_TIMEOUT_MS = 10_000
FIELD_LABELS = ("Main Disposition", "Sub Disposition", "Problem Type", "Description", "Attachment")
FIRST_OPTION = "Select"


class TicketModal(BasePage):
    def __init__(self, page: Page, title: str) -> None:
        super().__init__(page)
        self.dialog = page.get_by_role("dialog").filter(
            has=page.get_by_role("heading", name=title, exact=True)
        )

    def expect_open(self) -> None:
        expect(self.dialog).to_be_visible(timeout=MODAL_TIMEOUT_MS)

    def expect_closed(self) -> None:
        expect(self.dialog).to_have_count(0, timeout=MODAL_TIMEOUT_MS)

    def expect_fields(self) -> None:
        for label in FIELD_LABELS:
            expect(self.dialog.get_by_text(label).first).to_be_visible()
        expect(self.dialog.get_by_role("button", name="Save", exact=True)).to_be_visible()
        expect(self.dialog.get_by_role("button", name="Close", exact=True)).to_be_visible()

    def main_dispositions(self) -> list[str]:
        return self._options(self._main)

    def sub_dispositions(self) -> list[str]:
        return self._options(self._sub)

    def problem_types(self) -> list[str]:
        return self._options(self._problem)

    def choose_main_disposition(self, name: str) -> None:
        self._main.select_option(label=name)

    def choose_sub_disposition(self, name: str) -> None:
        self._sub.select_option(label=name)

    def choose_problem_type(self, name: str) -> None:
        self._problem.select_option(label=name)

    def expect_sub_disposition_focused(self) -> None:
        expect(self._sub).to_be_focused()

    def expect_description_focused(self) -> None:
        expect(self._description).to_be_focused()

    def expect_chosen(self, main: str, sub: str, problem: str) -> None:
        for select, name in ((self._main, main), (self._sub, sub), (self._problem, problem)):
            expect(select.locator("option:checked")).to_have_text(name)

    def write_description(self, text: str) -> None:
        """Fills at once: no key events, so no suggestion request."""
        self._description.fill(text)

    def type_description(self, text: str) -> None:
        """Key by key, the way the suggestion lookup (`keyup`) expects."""
        self._description.press_sequentially(text)

    def paste_description(self, text: str) -> None:
        """Inserts the text the way a paste does, so maxlength applies (a `fill` would bypass it)."""
        self._description.focus()
        self.page.keyboard.insert_text(text)

    def description(self) -> str:
        return self._description.input_value()

    def expect_description(self, text: str) -> None:
        expect(self._description).to_have_value(text)

    def attach(self, file: FilePayload) -> None:
        with self.page.expect_file_chooser() as chooser:
            self.dialog.get_by_role("button", name="Attachment").click()
        chooser.value.set_files(file)

    def expect_attached(self, file_name: str) -> None:
        expect(self._file_name).to_have_value(file_name)

    def expect_nothing_attached(self) -> None:
        expect(self._file_name).to_have_value("")

    def save(self) -> None:
        self.dialog.get_by_role("button", name="Save", exact=True).click()

    def double_click_save(self) -> None:
        self.dialog.get_by_role("button", name="Save", exact=True).dblclick()

    def update(self) -> None:
        self.dialog.get_by_role("button", name="Update", exact=True).click()

    def press_f10(self) -> None:
        self._description.press("F10")

    def close(self) -> None:
        self.dialog.get_by_role("button", name="Close", exact=True).click()

    def close_with_escape(self) -> None:
        self.page.keyboard.press("Escape")

    def expect_required_message(self, message: str) -> None:
        expect(self.page.get_by_role("tooltip").filter(has_text=message)).to_be_visible()

    def expect_no_required_marker_on_description(self) -> None:
        # Why CSS: the validation marker is a bare "!" anchor next to the field, with no role or label.
        marker = self.dialog.locator(".form-group", has=self._description).locator("a.errowMsgNew")
        expect(marker).to_have_count(0)

    def expect_suggestion(self, question: str, url: str) -> None:
        link = self._suggestions.get_by_role("link", name=question)
        expect(link).to_have_attribute("href", url)
        expect(link).to_have_attribute("target", "_blank")

    def expect_marked_word(self, word: str) -> None:
        expect(self._suggestions.locator("mark").filter(has_text=word).first).to_be_visible()

    def expect_no_suggestions(self) -> None:
        expect(self._suggestions).to_have_count(0)

    @property
    def _suggestions(self) -> Locator:
        return self.page.get_by_role("tooltip").filter(has_text=SUGGESTIONS_TITLE)

    @property
    def _main(self) -> Locator:
        return self.dialog.locator("#Main_Disposition")

    @property
    def _sub(self) -> Locator:
        return self.dialog.locator("#Sub_Disposition")

    @property
    def _problem(self) -> Locator:
        return self.dialog.locator("#ticket-support")

    @property
    def _description(self) -> Locator:
        return self.dialog.locator("#Description")

    @property
    def _file_name(self) -> Locator:
        return self.dialog.locator("#fileName")

    @staticmethod
    def _options(select: Locator) -> list[str]:
        expect(select.locator("option").first).to_have_text(FIRST_OPTION, timeout=MODAL_TIMEOUT_MS)
        return [text.strip() for text in select.locator("option").all_inner_texts()]
