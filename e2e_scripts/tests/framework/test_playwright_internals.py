"""Learning test (clean code ch. 8): the private Playwright names fixtures/steps.py relies on still exist.

If this fails after a Playwright upgrade, the console's "element state" panel would silently go empty.
"""

import pytest
from playwright.sync_api import Page, expect

from fixtures import steps

pytestmark = pytest.mark.framework


def test_failed_expect_exposes_its_locator_and_selector(page: Page) -> None:
    page.set_content("<header id='company'>Other Traders</header>")

    with pytest.raises(AssertionError) as excinfo:
        expect(page.locator("#company")).to_have_text("Demo Traders", timeout=200)

    state = steps._read_element_state(excinfo)

    assert state == {"locator": "#company", "text": "Other Traders", "visible": True}
