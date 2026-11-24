"""`assert_screenshot` sets the 1440x900 baseline viewport only for the shot, then restores the test's own."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from fixtures.visual import ScreenshotAsserter, ShotOptions, TestIdentity, VisualStore

pytestmark = pytest.mark.framework

PHONE = {"width": 390, "height": 844}


class SizedPage:
    def __init__(self) -> None:
        self.viewport_size: dict[str, int] | None = dict(PHONE)
        self.sizes: list[dict[str, int]] = []

    def set_viewport_size(self, size: dict[str, int]) -> None:
        self.sizes.append(dict(size))
        self.viewport_size = dict(size)

    def screenshot(self, **_: Any) -> bytes:
        buffer = io.BytesIO()
        Image.new("RGB", (1440, 900), (255, 255, 255)).save(buffer, format="PNG")
        return buffer.getvalue()


class FailingShotPage(SizedPage):
    def screenshot(self, **_: Any) -> bytes:
        raise RuntimeError("page closed during the screenshot")


def test_viewport_is_restored_when_the_screenshot_itself_raises(tmp_path: Path) -> None:
    who = TestIdentity(nodeid="tests/visual/x.py::test_x", module_dir="x", function="test_x")
    page = FailingShotPage()

    with pytest.raises(RuntimeError, match="page closed"):
        ScreenshotAsserter(VisualStore(tmp_path, "r1"), who)(page, "shot", ShotOptions())  # type: ignore[arg-type]

    assert page.sizes == [{"width": 1440, "height": 900}, PHONE]
    assert page.viewport_size == PHONE


def test_viewport_is_restored_after_the_screenshot_when_the_check_then_fails(tmp_path: Path) -> None:
    who = TestIdentity(nodeid="tests/visual/x.py::test_x", module_dir="x", function="test_x")
    page = SizedPage()

    with pytest.raises(pytest.fail.Exception, match="no baseline"):
        ScreenshotAsserter(VisualStore(tmp_path, "r1"), who)(page, "shot", ShotOptions())  # type: ignore[arg-type]

    assert page.sizes == [{"width": 1440, "height": 900}, PHONE]
    assert page.viewport_size == PHONE
