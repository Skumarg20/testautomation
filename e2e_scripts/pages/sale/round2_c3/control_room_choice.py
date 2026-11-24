"""A Dashboard > Control Room > Configure option with any choices, read and written by its Particulars text.

`ControlRoom._set_option` already writes a drop-down chosen from the search box; here the choice may be any of
the option's texts or values (not only Yes / No), the original is read first and put back afterwards, and a
choice the tenant does not offer is an error that lists what it does offer (the lists are API data).
Locators are those of `ControlRoom` and `ControlRoomState`; unverified live for options other than Yes / No.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from playwright.sync_api import Locator

from pages.settings.control_room import ControlRoom


class ChoiceNotOfferedError(LookupError):
    def __init__(self, name: str, wanted: str, offered: list[str]) -> None:
        super().__init__(f'Control Room "{name}" has no choice "{wanted}"; it offers {offered}')


class ChoiceNotRestoredError(AssertionError):
    def __init__(self, name: str, original: str, now: str) -> None:
        super().__init__(f'Control Room "{name}" is "{now}" after the restore, it was "{original}"')


@dataclass(frozen=True)
class Choice:
    """A Control Room option by its Particulars text, and the choice a test needs."""

    name: str
    wanted: str


HoldChoice = Callable[[Choice], None]
"""What the `control_room` fixture offers a test: hold this choice until the test ends."""


class ControlRoomChoices(ControlRoom):
    def current(self, name: str) -> str:
        """The shown text of the option; the Control Room is left with Escape, which changes nothing."""
        dropdown = self._open(name)
        # Why CSS: a select exposes its chosen option only through the :checked state.
        text = dropdown.locator("option:checked").inner_text().strip()
        self.page.keyboard.press("Escape")
        return text

    def offered(self, name: str) -> list[str]:
        dropdown = self._open(name)
        texts = [text.strip() for text in dropdown.locator("option").all_inner_texts()]
        self.page.keyboard.press("Escape")
        return texts

    def choose(self, name: str, wanted: str) -> None:
        """`wanted` is an option's text; a choice not on offer raises before anything is saved."""
        offered = self.offered(name)
        match = [text for text in offered if text.casefold() == wanted.casefold()]
        if not match:
            raise ChoiceNotOfferedError(name, wanted, offered)
        self._set_option(name, match[0])

    def _open(self, name: str) -> Locator:
        self.page.wait_for_load_state("load")
        self.open_button.click()
        self.configure_button.click()
        self.search.click()
        self.search.press_sequentially(name)
        return self._dropdown_for(name)


@contextmanager
def choice_held(
    choices: ControlRoomChoices, choice: Choice, before_restore: Callable[[], None]
) -> Iterator[str]:
    """Yields the original text. `before_restore` brings the page to where the Control Room opens from."""
    original = choices.current(choice.name)
    if original.casefold() == choice.wanted.casefold():
        yield original
        return
    try:
        # Inside the try: a save that fails half-way may still have changed the tenant.
        choices.choose(choice.name, choice.wanted)
        yield original
    finally:
        before_restore()
        choices.choose(choice.name, original)
        now = choices.current(choice.name)
        if now.casefold() != original.casefold():
            raise ChoiceNotRestoredError(choice.name, original, now)
