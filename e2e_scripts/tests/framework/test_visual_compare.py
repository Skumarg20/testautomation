"""Framework checks for the visual comparator and `assert_screenshot` (F06 6.2, 6.3). No app needed."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image, ImageDraw
from pixelmatch.contrib.PIL import pixelmatch

from fixtures.visual import (
    ScreenshotAsserter,
    ShotOptions,
    TestIdentity,
    VisualStore,
    baseline_rel_path,
    safe_segment,
)
from visual.compare import FAIL_COLOUR, changed_pct, compare_files, compare_images, is_over_threshold

pytestmark = pytest.mark.framework

WIDTH, HEIGHT = 1440, 900
TOTAL = WIDTH * HEIGHT
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def canvas(size: tuple[int, int] = (WIDTH, HEIGHT)) -> Image.Image:
    return Image.new("RGB", size, WHITE)


def with_block(width: int, height: int) -> Image.Image:
    image = canvas()
    ImageDraw.Draw(image).rectangle((0, 0, width - 1, height - 1), fill=BLACK)
    return image


def rgb(image: Image.Image, xy: tuple[int, int]) -> tuple[int, ...]:
    value = image.getpixel(xy)
    assert isinstance(value, tuple)
    return value[:3]


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_identical_images_give_0_pct_and_unchanged() -> None:
    result = compare_images(canvas(), canvas())

    assert (result.diff_pixels, result.changed_pct, result.unchanged) == (0, 0.0, True)


def test_23328_differing_pixels_on_1440x900_give_1_8() -> None:
    result = compare_images(canvas(), with_block(144, 162))

    assert result.diff_pixels == 23_328
    assert result.total_pixels == 1_296_000
    assert result.changed_pct == pytest.approx(1.8)
    assert is_over_threshold(result.diff_pixels, result.total_pixels, 0.2)


def test_1296_differing_pixels_give_0_1_and_stay_within_threshold() -> None:
    result = compare_images(canvas(), with_block(36, 36))

    assert result.diff_pixels == 1_296
    assert result.changed_pct == pytest.approx(0.1)
    assert not is_over_threshold(result.diff_pixels, result.total_pixels, 0.2)


@pytest.mark.parametrize(("pixels", "over"), [(2_592, False), (2_593, True)])
def test_threshold_boundary_is_exactly_0_2_pct(pixels: int, over: bool) -> None:
    assert changed_pct(2_592, TOTAL) == pytest.approx(0.2)
    assert is_over_threshold(pixels, TOTAL, 0.2) is over


def test_anti_aliasing_only_difference_not_counted() -> None:
    def line(shift: int) -> Image.Image:
        big = Image.new("RGB", (800, 800), WHITE)
        ImageDraw.Draw(big).line((0, 100 + shift, 800, 500 + shift), fill=BLACK, width=14)
        return big.resize((100, 100), Image.Resampling.BOX)

    ours = compare_images(line(0), line(1))
    counting_aa = pixelmatch(line(0), line(1), None, threshold=0.1, includeAA=True)

    assert ours.diff_pixels < 5
    assert counting_aa > 100


def test_size_mismatch_gives_100_and_flag_without_diff_image(tmp_path: Path) -> None:
    diff = tmp_path / "diff.png"

    result = compare_images(canvas(), canvas((WIDTH, HEIGHT + 10)), diff)

    assert result.size_mismatch is True
    assert result.changed_pct == 100.0
    assert not result.unchanged
    assert not diff.exists()


def test_diff_image_highlights_in_fail_colour_only_on_differing_pixels(tmp_path: Path) -> None:
    baseline, actual, diff = tmp_path / "b.png", tmp_path / "a.png", tmp_path / "d.png"
    canvas().save(baseline)
    with_block(10, 10).save(actual)

    result = compare_files(baseline, actual, diff)

    with Image.open(diff) as image:
        rgba = image.convert("RGBA")
        corner = [(x, y) for x in range(20) for y in range(20)]
        marked = [xy for xy in corner if rgb(rgba, xy) == FAIL_COLOUR]
        assert len(marked) == result.diff_pixels == 100
        assert all(x < 10 and y < 10 for x, y in marked)
        assert rgb(rgba, (500, 500)) != FAIL_COLOUR


# ----- assert_screenshot ------------------------------------------------------------------------------


class FakePage:
    def __init__(self, png: bytes) -> None:
        self.png = png
        self.viewport: dict[str, int] | None = None
        self.screenshot_kwargs: dict[str, Any] = {}

    def set_viewport_size(self, size: dict[str, int]) -> None:
        self.viewport = size

    def screenshot(self, **kwargs: Any) -> bytes:
        self.screenshot_kwargs = kwargs
        return self.png


def who() -> TestIdentity:
    return TestIdentity(
        nodeid="tests/journeys/sales/test_sale_grid.py::test_grid_layout",
        module_dir="sales/test_sale_grid",
        function="test_grid_layout",
    )


@pytest.fixture
def store(tmp_path: Path) -> VisualStore:
    return VisualStore(tmp_path, "local-1006")


def asserter(store: VisualStore) -> ScreenshotAsserter:
    return ScreenshotAsserter(store, who())


def put_baseline(store: VisualStore, image: Image.Image, name: str = "grid") -> Path:
    path = store.baselines / baseline_rel_path(who(), name)
    path.parent.mkdir(parents=True)
    image.save(path)
    return path


def manifest(store: VisualStore) -> list[dict[str, Any]]:
    return json.loads((store.run_dir / "manifest.json").read_text())["entries"]  # type: ignore[no-any-return]


def test_baseline_path_follows_the_documented_layout() -> None:
    rel = baseline_rel_path(who(), "")

    assert rel == "sales/test_sale_grid/test_grid_layout--1440x900--chromium.png"
    assert baseline_rel_path(who(), "Sale bill grid") == (
        "sales/test_sale_grid/test_grid_layout--Sale-bill-grid--1440x900--chromium.png"
    )


@pytest.mark.parametrize("text", ["../etc/passwd", "a/b", "..", "x\\y", "ok name"])
def test_safe_segment_never_has_separators_or_dotdot(text: str) -> None:
    segment = safe_segment(text)

    assert ".." not in segment
    assert "/" not in segment
    assert "\\" not in segment


def test_missing_baseline_fails_test_and_writes_no_baseline(store: VisualStore) -> None:
    with pytest.raises(pytest.fail.Exception, match="no baseline"):
        asserter(store).check(png_bytes(canvas()), "grid", ShotOptions())

    assert not store.baselines.exists()
    entry = manifest(store)[0]
    assert entry["noBaseline"] is True
    assert entry["changedPct"] is None
    assert (store.entry_dir(entry["baselineRelPath"]) / "actual.png").is_file()


def test_helper_masks_and_disables_animations(store: VisualStore) -> None:
    put_baseline(store, canvas())
    page = FakePage(png_bytes(canvas()))
    mask = object()

    asserter(store)(page, "grid", ShotOptions(mask=[mask]))  # type: ignore[arg-type,list-item]

    assert page.viewport == {"width": 1440, "height": 900}
    assert page.screenshot_kwargs["animations"] == "disabled"
    assert page.screenshot_kwargs["caret"] == "hide"
    assert page.screenshot_kwargs["mask"] == [mask]


def test_within_threshold_passes_and_records_files_and_manifest(store: VisualStore) -> None:
    baseline = put_baseline(store, canvas())

    asserter(store).check(png_bytes(with_block(36, 36)), "grid", ShotOptions(account="chemist"))

    entry = manifest(store)[0]
    folder = store.entry_dir(entry["baselineRelPath"])
    assert {p.name for p in folder.iterdir()} == {"baseline.png", "actual.png", "diff.png"}
    assert (folder / "baseline.png").read_bytes() == baseline.read_bytes()
    assert entry["diffPixels"] == 1_296
    assert entry["totalPixels"] == TOTAL
    assert entry["changedPct"] == pytest.approx(0.1)
    assert entry["account"] == "chemist"
    assert entry["nodeid"] == who().nodeid
    assert set(entry["files"]) == {"baseline", "actual", "diff"}


def test_over_threshold_fails_and_leaves_baseline_untouched(store: VisualStore) -> None:
    baseline = put_baseline(store, canvas())
    before = baseline.read_bytes()

    with pytest.raises(pytest.fail.Exception, match="over the 0.2% threshold"):
        asserter(store).check(png_bytes(with_block(144, 162)), "grid", ShotOptions())

    assert baseline.read_bytes() == before
    assert manifest(store)[0]["diffPixels"] == 23_328


def test_exactly_2592_pixels_is_within_threshold(store: VisualStore) -> None:
    put_baseline(store, canvas())

    asserter(store).check(png_bytes(with_block(48, 54)), "grid", ShotOptions())  # 48 x 54 = 2,592


def test_size_mismatch_fails_without_diff_file(store: VisualStore) -> None:
    put_baseline(store, canvas())

    with pytest.raises(pytest.fail.Exception, match="size mismatch"):
        asserter(store).check(png_bytes(canvas((WIDTH, 800))), "grid", ShotOptions())

    entry = manifest(store)[0]
    assert entry["sizeMismatch"] is True
    assert entry["changedPct"] == 100.0
    assert "diff" not in entry["files"]


def test_rerun_replaces_the_manifest_entry(store: VisualStore) -> None:
    put_baseline(store, canvas())

    asserter(store).check(png_bytes(canvas()), "grid", ShotOptions())
    asserter(store).check(png_bytes(with_block(10, 10)), "grid", ShotOptions())

    entries = manifest(store)
    assert len(entries) == 1
    assert entries[0]["diffPixels"] == 100
