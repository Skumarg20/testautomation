"""`assert_screenshot`: compare a page screenshot with its approved baseline (F06 section 6).

A baseline is never written here. A missing baseline fails the test with "no baseline"; the baseline is
created only by the console's approve flow or an explicit developer copy, so a first run cannot pass by
writing its own expected value.

Run output goes to `results/visual/<runId>/<baseline path without .png>/{baseline,actual,diff}.png` and one
entry per screenshot is added to `results/visual/<runId>/manifest.json`, which the console ingests.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Locator, Page

from visual.compare import (
    DEFAULT_THRESHOLD_PCT,
    Comparison,
    compare_files,
    is_over_threshold,
    sha256_of,
)


try:
    import fcntl
except ImportError:  # Windows has no fcntl; msvcrt locks a byte of the lock file instead
    fcntl = None  # type: ignore[assignment]
    import msvcrt


def _lock_exclusive(fileno: int) -> None:
    if fcntl:
        fcntl.flock(fileno, fcntl.LOCK_EX)
    else:
        msvcrt.locking(fileno, msvcrt.LK_LOCK, 1)


def _unlock(fileno: int) -> None:
    if fcntl:
        fcntl.flock(fileno, fcntl.LOCK_UN)
    else:
        msvcrt.locking(fileno, msvcrt.LK_UNLCK, 1)

VIEWPORT = {"width": 1440, "height": 900}
VIEWPORT_LABEL = "1440x900"
RUN_ID_ENV = "CONSOLE_RUN_ID"
DEFAULT_RUN_ID = "local"
E2E_DIR = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "manifest.json"
_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_segment(text: str) -> str:
    """A path segment made of `[A-Za-z0-9_.-]` only, never containing `..`."""
    cleaned = _UNSAFE.sub("-", text).strip("-.")
    while ".." in cleaned:
        cleaned = cleaned.replace("..", ".")
    return cleaned


@dataclass(frozen=True)
class ShotOptions:
    account: str = "all"
    threshold_pct: float = DEFAULT_THRESHOLD_PCT
    mask: Sequence[Locator] = ()
    full_page: bool = False


@dataclass(frozen=True)
class TestIdentity:
    __test__ = False  # not a pytest class

    nodeid: str
    module_dir: str  # e.g. "sales/test_sale_grid"
    function: str  # the test function name without parameters
    param_id: str | None = None
    browser: str = "chromium"


def identity_from_request(request: pytest.FixtureRequest, browser: str) -> TestIdentity:
    node = request.node
    tests_dir = E2E_DIR / "tests"
    path = Path(str(node.path))
    inside = path.is_relative_to(tests_dir)
    parts = list(path.relative_to(tests_dir).with_suffix("").parts) if inside else [path.stem]
    module_dir = "/".join(safe_segment(p) for p in (parts[1:] or parts))  # drop the layer folder
    callspec = getattr(node, "callspec", None)
    return TestIdentity(
        nodeid=node.nodeid,
        module_dir=module_dir,
        function=safe_segment(getattr(node, "originalname", None) or node.name),
        param_id=safe_segment(callspec.id) if callspec else None,
        browser=safe_segment(browser) or "chromium",
    )


def baseline_rel_path(who: TestIdentity, name: str) -> str:
    """`<module>/<test-module>/<test>[--<param>][--<name>]--<viewport>--<browser>.png`, under baselines/."""
    extras = [p for p in (who.param_id, safe_segment(name)) if p]
    pieces = [who.function, *extras, VIEWPORT_LABEL, who.browser]
    return f"{who.module_dir}/{'--'.join(pieces)}.png"


class VisualStore:
    """Where baselines and run output live. Tests point it at a temporary directory."""

    def __init__(self, e2e_dir: Path, run_id: str) -> None:
        self.baselines = e2e_dir / "visual" / "baselines"
        self.run_dir = e2e_dir / "results" / "visual" / run_id
        self.run_id = run_id

    def entry_dir(self, rel_png: str) -> Path:
        return self.run_dir / rel_png.removesuffix(".png")

    @contextlib.contextmanager
    def _locked(self) -> Iterator[None]:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        with (self.run_dir / ".manifest.lock").open("w") as lock:
            _lock_exclusive(lock.fileno())
            try:
                yield
            finally:
                _unlock(lock.fileno())

    def add_entry(self, entry: dict[str, Any]) -> None:
        """Add or replace (same baseline path, e.g. a rerun) one entry; safe under xdist workers."""
        manifest_path = self.run_dir / MANIFEST_NAME
        with self._locked():
            entries: list[dict[str, Any]] = []
            if manifest_path.exists():
                entries = json.loads(manifest_path.read_text())["entries"]
            entries = [e for e in entries if e["baselineRelPath"] != entry["baselineRelPath"]]
            entries.append(entry)
            temp = manifest_path.with_suffix(".tmp")
            temp.write_text(json.dumps({"runId": self.run_id, "entries": entries}, indent=2))
            os.replace(temp, manifest_path)


@dataclass
class ScreenshotAsserter:
    store: VisualStore
    who: TestIdentity
    _taken: list[str] = field(default_factory=list)

    def __call__(self, page: Page, name: str, options: ShotOptions | None = None) -> Comparison | None:
        opts = options or ShotOptions()
        previous = getattr(page, "viewport_size", None)  # None: no fixed viewport to give back
        page.set_viewport_size(VIEWPORT)  # type: ignore[arg-type]
        try:
            png = page.screenshot(
                animations="disabled",
                caret="hide",
                mask=list(opts.mask),
                full_page=opts.full_page,
                type="png",
            )
        finally:
            if previous is not None:
                page.set_viewport_size(previous)
        return self.check(png, name, opts)

    def check(self, png: bytes, name: str, opts: ShotOptions) -> Comparison | None:
        rel = baseline_rel_path(self.who, name)
        if rel in self._taken:
            pytest.fail(f"screenshot name '{name}' is used twice in one test; give each a distinct name")
        self._taken.append(rel)
        folder = self.store.entry_dir(rel)
        folder.mkdir(parents=True, exist_ok=True)
        actual = folder / "actual.png"
        actual.write_bytes(png)
        baseline = self.store.baselines / rel
        entry = self._entry(name, rel, opts)
        if not baseline.is_file():
            entry.update(noBaseline=True, files={"actual": self._rel(actual)}, actualSha256=sha256_of(actual))
            self.store.add_entry(entry)
            pytest.fail(f"no baseline for '{name}' at visual/baselines/{rel}; approve it in the console")
        result = self._compare(baseline, folder, entry)
        self.store.add_entry(entry)
        self._assert_within(result, opts, rel)
        return result

    def _compare(self, baseline: Path, folder: Path, entry: dict[str, Any]) -> Comparison:
        shutil.copyfile(baseline, folder / "baseline.png")
        result = compare_files(folder / "baseline.png", folder / "actual.png", folder / "diff.png")
        files = {"baseline": self._rel(folder / "baseline.png"), "actual": self._rel(folder / "actual.png")}
        if not result.size_mismatch:
            files["diff"] = self._rel(folder / "diff.png")
        entry.update(
            changedPct=round(result.changed_pct, 4),
            diffPixels=result.diff_pixels,
            totalPixels=result.total_pixels,
            sizeMismatch=result.size_mismatch,
            files=files,
            baselineSha256=sha256_of(folder / "baseline.png"),
            actualSha256=sha256_of(folder / "actual.png"),
        )
        return result

    def _entry(self, name: str, rel: str, opts: ShotOptions) -> dict[str, Any]:
        return {
            "name": name,
            "account": opts.account,
            "browser": self.who.browser,
            "viewport": VIEWPORT_LABEL,
            "thresholdPct": opts.threshold_pct,
            "changedPct": None,
            "diffPixels": None,
            "totalPixels": None,
            "baselineRelPath": rel,
            "files": {},
            "nodeid": self.who.nodeid,
            "sizeMismatch": False,
            "noBaseline": False,
        }

    def _rel(self, path: Path) -> str:
        return path.relative_to(self.store.run_dir).as_posix()

    @staticmethod
    def _assert_within(result: Comparison, opts: ShotOptions, rel: str) -> None:
        if result.size_mismatch:
            pytest.fail(
                f"size mismatch for {rel}: baseline {result.baseline_size}, actual {result.actual_size}"
            )
        if is_over_threshold(result.diff_pixels, result.total_pixels, opts.threshold_pct):
            pytest.fail(
                f"{result.changed_pct:.2f}% of pixels differ ({result.diff_pixels:,}), "
                f"over the {opts.threshold_pct}% threshold: {rel}"
            )


def _browser_name(page: Page) -> str:
    browser = page.context.browser
    return browser.browser_type.name if browser else "chromium"


@pytest.fixture
def visual_store() -> VisualStore:
    return VisualStore(E2E_DIR, os.environ.get(RUN_ID_ENV, DEFAULT_RUN_ID))


@pytest.fixture
def assert_screenshot(
    request: pytest.FixtureRequest, visual_store: VisualStore
) -> Callable[[Page, str, ShotOptions | None], Comparison | None]:
    """Use as `assert_screenshot(page, "Sale bill grid")` or with `ShotOptions(account=..., mask=[...])`."""
    holder: dict[str, ScreenshotAsserter] = {}

    def run(page: Page, name: str, options: ShotOptions | None = None) -> Comparison | None:
        if "asserter" not in holder:
            who = identity_from_request(request, _browser_name(page))
            holder["asserter"] = ScreenshotAsserter(visual_store, who)
        return holder["asserter"](page, name, options)

    return run
