"""Typing into the app's live search boxes, which filter while one types and can drop keystrokes."""

from playwright.sync_api import Locator

KEY_DELAY_MS = 150
ATTEMPTS = 3


class SearchTextLostError(AssertionError):
    def __init__(self, text: str, shown: str) -> None:
        super().__init__(f'Search box shows "{shown}" after typing "{text}" {ATTEMPTS} times')


def type_search(box: Locator, text: str) -> None:
    """Types slowly and retypes when the box does not end up holding exactly the text.

    Never `fill("")`: clearing sends a Delete key, and these windows answer Delete with "Are you sure you
    want to delete the selected Record?" for the highlighted row (seen live 2026-10-08). Typing over a
    Control+A selection replaces the old text without a Delete key.
    """
    shown = ""
    for _ in range(ATTEMPTS):
        box.click()
        box.press("Control+A")
        box.press_sequentially(text, delay=KEY_DELAY_MS)
        shown = box.input_value()
        if shown == text:
            return
    raise SearchTextLostError(text, shown)
