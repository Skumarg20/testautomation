"""Finding the labelled header and footer inputs of a purchase document."""

from playwright.sync_api import Locator, Page


def labelled_input(page: Page, label: str) -> Locator:
    """The app's labels are not tied to their inputs, so the input is found next to its label."""
    return page.locator(
        f"xpath=//label[contains(normalize-space(), '{label}')]"
        "/ancestor::*[self::div or self::span][1]//input"
    ).first
