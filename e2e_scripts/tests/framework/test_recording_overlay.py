"""The recording overlay marks the cursor and every click so a video shows where the test clicks."""

import pytest
from playwright.sync_api import Page, expect

from fixtures.recording import CLICK_RING_ID, CURSOR_DOT_ID, OVERLAY_SCRIPT

pytestmark = pytest.mark.framework

PAGE = "<button id='go' style='margin:80px'>Go</button>"


def test_cursor_dot_follows_the_mouse(page: Page) -> None:
    page.add_init_script(OVERLAY_SCRIPT)
    page.goto("data:text/html," + PAGE)
    page.mouse.move(40, 50)
    expect(page.locator(f"#{CURSOR_DOT_ID}")).to_be_attached()


def test_click_flashes_a_ring(page: Page) -> None:
    page.add_init_script(OVERLAY_SCRIPT)
    page.goto("data:text/html," + PAGE)
    page.locator("#go").click()
    expect(page.locator(f"#{CLICK_RING_ID}")).to_be_attached()
