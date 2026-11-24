"""Pure screenshot comparison (F06 section 6.3): pixelmatch, YIQ threshold 0.1, anti-aliasing ignored.

No Playwright, no pytest, no environment: two images in, a `Comparison` out. The diff image is written only
when asked for and only when both images have the same size.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from PIL import Image
from pixelmatch.contrib.PIL import pixelmatch

FAIL_COLOUR = (200, 38, 91)  # #C8265B, the console's --fail colour
FADED_GREY = (236, 236, 236)  # anti-aliasing pixels are ignored, so they are not highlighted
PIXEL_TOLERANCE = 0.1  # YIQ distance, the pixelmatch default
FADE_ALPHA = 0.1  # opacity of the baseline behind the highlighted pixels
DEFAULT_THRESHOLD_PCT = 0.2


@dataclass(frozen=True)
class Comparison:
    diff_pixels: int
    total_pixels: int  # width x height of the baseline
    size_mismatch: bool
    baseline_size: tuple[int, int]
    actual_size: tuple[int, int]

    @property
    def changed_pct(self) -> float:
        return changed_pct(self.diff_pixels, self.total_pixels)

    @property
    def unchanged(self) -> bool:
        return self.diff_pixels == 0 and not self.size_mismatch


def changed_pct(diff_pixels: int, total_pixels: int) -> float:
    """differing / total * 100, unrounded. An empty baseline counts as fully changed."""
    return diff_pixels / total_pixels * 100 if total_pixels else 100.0


def is_over_threshold(diff_pixels: int, total_pixels: int, threshold_pct: float) -> bool:
    """Exact decimal comparison: 2,592 of 1,296,000 pixels is exactly 0.2% and is within threshold."""
    return Decimal(diff_pixels) * 100 > Decimal(str(threshold_pct)) * total_pixels


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_images(baseline: Image.Image, actual: Image.Image, diff_path: Path | None = None) -> Comparison:
    """Compare two images. A size mismatch is a full failure: 100 %, no diff image."""
    total = baseline.width * baseline.height
    if baseline.size != actual.size:
        return Comparison(total, total, True, baseline.size, actual.size)
    base, new = baseline.convert("RGBA"), actual.convert("RGBA")
    output = Image.new("RGBA", base.size) if diff_path else None
    count = pixelmatch(
        base,
        new,
        output,
        threshold=PIXEL_TOLERANCE,
        includeAA=False,
        alpha=FADE_ALPHA,
        aa_color=FADED_GREY,
        diff_color=FAIL_COLOUR,
    )
    if output is not None and diff_path is not None:
        diff_path.parent.mkdir(parents=True, exist_ok=True)
        output.save(diff_path, format="PNG")
    return Comparison(count, total, False, base.size, new.size)


def compare_files(baseline_path: Path, actual_path: Path, diff_path: Path | None = None) -> Comparison:
    with Image.open(baseline_path) as baseline, Image.open(actual_path) as actual:
        return compare_images(baseline, actual, diff_path)
