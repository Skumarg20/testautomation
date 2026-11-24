"""Test Studio live steps: every browser action and check of a script becomes a step with a screenshot.

Active only when Test Studio runs the script (STUDIO_LIVE_DIR is set). Each Playwright action (goto, click, fill,
press, select...) and each expect() check is written as one line of `steps.jsonl` in that folder, with a screenshot
taken right after it (`stepNNN.png`), so Test Studio shows the run like its own: live steps, the live screen, and
a report with every step's screenshot. Values typed into password boxes, and the run's own logins, are shown as ***.
"""

from __future__ import annotations

import functools
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable

LIVE_DIR = os.environ.get("STUDIO_LIVE_DIR", "")
SHOT_TIMEOUT_MS = 3000
MAX_STEPS = 400

PAGE_ACTIONS = ("goto", "reload", "go_back", "go_forward")
LOCATOR_ACTIONS = ("click", "dblclick", "fill", "type", "press", "press_sequentially", "check", "uncheck",
                   "select_option", "set_input_files", "hover", "clear", "select_text", "tap")
KEYBOARD_ACTIONS = ("press", "type", "insert_text")
TYPED = {"fill", "type", "press_sequentially", "insert_text"}

_state = threading.local()
_lock = threading.Lock()
_count = {"n": 0}
_last_page: dict[str, Any] = {"page": None}


def _secrets() -> set[str]:
    return {v for k, v in os.environ.items() if re.match(r"QA_\w+_(PASS|USER)$", k) and v and len(v) > 3}


def _regex_words(pattern: str) -> str:
    """The plain words of a name regex: /^\\s*Create\\/F2\\s*$/i -> Create/F2, /^Sale( Sale)?$/ -> Sale."""
    words = re.sub(r"\([^)]*\)\??|\\s[*+?]?|[\^$]|\\(?=[/\\.])", "", pattern)
    return re.sub(r"\\", "", words).strip()


def _pretty(selector: str) -> str:
    s = selector.replace('\\"', '"')
    s = re.sub(r"internal:role=(\w+)\[name=/(.+?)/[a-z]*\]", lambda m: f'{m.group(1)} "{_regex_words(m.group(2))}"', s)
    s = re.sub(r'internal:has="\[col-id="(\w+)"\]\s*>>?\s*internal:has-text=/(.+?)/[a-z]*"',
               lambda m: f'with {m.group(1)} "{_regex_words(m.group(2))}"', s)
    s = re.sub(r'internal:has="\[col-id="(\w+)"\]"', r"with a \1 cell", s)
    s = re.sub(r'internal:has-text=/(.+?)/[a-z]*', lambda m: f'with text "{_regex_words(m.group(1))}"', s)
    s = s.replace(":root", "the page")
    s = re.sub(r'internal:role=(\w+)\[name="([^"]*)"[is]?\]', r'\1 "\2"', s)
    s = re.sub(r"internal:role=(\w+)", r"\1", s)
    s = re.sub(r'internal:(text|label)="([^"]*)"[is]?', r'\1 "\2"', s)
    s = re.sub(r'internal:attr=\[(\w+)="([^"]*)"[is]?\]', r'\1 "\2"', s)
    s = re.sub(r"internal:has-text=", "with text ", s)
    s = s.replace(" >> nth=0", " (first)").replace(" >> ", " > ")
    return s[:140]


def _selector(locator: Any) -> str:
    m = re.search(r"selector='(.*)'>?$", repr(locator), re.S)
    return _pretty(m.group(1) if m else repr(locator))


def _value(action: str, selector: str, args: tuple, kwargs: dict) -> str:
    if action not in TYPED and action not in ("press", "select_option"):
        return ""
    value = str(args[0] if args else kwargs.get("value", kwargs.get("text", kwargs.get("key", ""))))
    if action in TYPED and ("password" in selector.lower() or value in _secrets()):
        return "***"
    return value[:60]


def _write(entry: dict[str, Any]) -> None:
    with _lock, open(Path(LIVE_DIR) / "steps.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _shot(page: Any, n: int) -> str:
    if page is None:
        return ""
    name = f"step{n:03d}.png"
    try:
        page.screenshot(path=str(Path(LIVE_DIR) / name), timeout=SHOT_TIMEOUT_MS)
        return name
    except Exception:  # noqa: BLE001  (a closed or busy page: the step still counts)
        return ""


def _record(text: str, page: Any, call: Callable[[], Any]) -> Any:
    """Run one action as a step. Nested actions (Playwright calling itself) are not separate steps."""
    if getattr(_state, "depth", 0) or _count["n"] >= MAX_STEPS:
        return call()
    _state.depth = 1
    t0 = time.time()
    try:
        result = call()
    except BaseException as error:
        _state.depth = 0
        _count["n"] += 1
        n = _count["n"]
        _write({"n": n, "text": text, "status": "bad", "secs": round(time.time() - t0, 1), "shot": _shot(page, n),
                "error": str(error).split("\n")[0][:300]})
        raise
    _state.depth = 0
    _count["n"] += 1
    n = _count["n"]
    _write({"n": n, "text": text, "status": "ok", "secs": round(time.time() - t0, 1), "shot": _shot(page, n)})
    return result


def _wrap(cls: Any, name: str, describe: Callable[..., tuple[str, Any]]) -> None:
    original = getattr(cls, name, None)
    if original is None or getattr(original, "_studio_live", False):
        return

    @functools.wraps(original)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        text, page = describe(self, name, args, kwargs)
        if page is not None:
            _last_page["page"] = page
        return _record(text, page if page is not None else _last_page["page"],
                       lambda: original(self, *args, **kwargs))

    wrapper._studio_live = True  # type: ignore[attr-defined]
    setattr(cls, name, wrapper)


def _page_text(page: Any, name: str, args: tuple, kwargs: dict) -> tuple[str, Any]:
    url = str(args[0] if args else kwargs.get("url", ""))
    return (f"Open {url}" if name == "goto" else name.replace("_", " ").capitalize()), page


def _locator_text(locator: Any, name: str, args: tuple, kwargs: dict) -> tuple[str, Any]:
    sel = _selector(locator)
    value = _value(name, sel, args, kwargs)
    verb = {"fill": "Type", "type": "Type", "press_sequentially": "Type", "press": "Press", "select_option": "Choose",
            "set_input_files": "Upload file in", "dblclick": "Double-click"}.get(name, name.replace("_", " ").capitalize())
    text = f'{verb} "{value}" in {sel}' if value and name in TYPED | {"select_option"} else \
        f"{verb} {value} on {sel}" if value else f"{verb} {sel}"
    return text, getattr(locator, "page", None)


def _keyboard_text(_kb: Any, name: str, args: tuple, kwargs: dict) -> tuple[str, Any]:
    value = str(args[0] if args else kwargs.get("key", kwargs.get("text", "")))
    if name != "press" and value in _secrets():
        value = "***"
    return (f"Press {value}" if name == "press" else f'Type "{value[:60]}"'), None


def _expect_text(assertion: Any, name: str, args: tuple, kwargs: dict) -> tuple[str, Any]:
    target = getattr(getattr(assertion, "_impl_obj", None), "_actual_locator", None)
    what = _selector(target) if target is not None else "the page"
    check = name.replace("not_to_", "not ").replace("to_", "", 1).replace("_", " ")
    shown = args[0] if args else None
    if hasattr(shown, "pattern"):                             # re.compile('/dashboard') -> /dashboard
        shown = getattr(shown, "pattern")
    expected = f' "{str(shown)[:80]}"' if shown is not None else ""
    # the assertion holds the async-side objects: the screenshot is taken on the last page an action used
    return f"Check {what}: {check}{expected}", None


def install() -> None:
    from playwright.sync_api import Keyboard, Locator, Page
    from playwright.sync_api._generated import LocatorAssertions, PageAssertions

    for name in PAGE_ACTIONS:
        _wrap(Page, name, _page_text)
    for name in LOCATOR_ACTIONS:
        _wrap(Locator, name, _locator_text)
    for name in KEYBOARD_ACTIONS:
        _wrap(Keyboard, name, _keyboard_text)
    for cls in (LocatorAssertions, PageAssertions):
        for name in [n for n in dir(cls) if n.startswith(("to_", "not_to_"))]:
            _wrap(cls, name, _expect_text)


if LIVE_DIR:
    Path(LIVE_DIR).mkdir(parents=True, exist_ok=True)
    install()
