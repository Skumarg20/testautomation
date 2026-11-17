"""
Excel / CSV se test import.

Tester ko YAML nahi likhni. Wo ek simple sheet bharta hai:

  Test Name | Description | Module | Action | Screen/Field | Value | Expected

Ek test ke saare step ek ke neeche ek. Naya test tab shuru hota hai jab
"Test Name" dobara bhara ho. Beech ki khali rows usi test ke steps hain.
"""
from __future__ import annotations

import csv
import io

from framework.screens import SCREENS
from framework.locator_store import store as locators

ACTIONS = ["open_screen", "open_menu", "goto", "click", "fill", "select", "press",
           "wait_text", "assert_text", "assert_no_text", "assert_visible",
           "assert_not_visible", "sleep", "screenshot", "note",
           # transaction form ke liye -- grid me seedha fill kaam nahi karta
           "set_party", "fill_header", "add_item", "add_barcode", "pick_batch",
           "retail_bill", "expect_party_state", "ensure_party", "require_setting",
           "set_bill_discount", "expect_total", "expect_lines", "expect_trade",
           "expect_field", "expect_no_field", "expect_column",
           "close_form", "save_form"]

# tester ke aam shabd -> asli action
ALIASES = {
    "kholo": "open_screen", "open": "open_screen", "screen": "open_screen",
    "jao": "goto", "navigate": "goto",
    "dabao": "click", "press button": "click", "tap": "click",
    "bharo": "fill", "type": "fill", "enter": "fill", "likho": "fill",
    "chuno": "select", "choose": "select", "dropdown": "select",
    "dikhna chahiye": "assert_text", "check text": "assert_text",
    "verify": "assert_text", "should see": "assert_text",
    "nahi dikhna chahiye": "assert_no_text", "should not see": "assert_no_text",
    "ruko": "sleep", "wait": "sleep", "pause": "sleep",
    "party set karo": "set_party", "set party": "set_party",
    "item jodo": "add_item", "add item": "add_item",
    "bill band karo": "close_form", "close bill": "close_form",
    "total check": "expect_total",
    "go to": "goto", "click on": "click", "fill in": "fill",
    "select from": "select", "assert": "assert_text",
}

HEADERS = ["Test Name", "Description", "Module", "Action",
           "Screen/Field", "Value", "Expected"]


def template_csv() -> str:
    """Khali sheet jo tester bhar sake."""
    rows = [
        HEADERS,
        ["Item search finds an item", "Searching Sample Item should show it",
         "masters", "open_screen", "item", "", ""],
        ["", "", "", "fill", "item.search", "Sample Item", ""],
        ["", "", "", "sleep", "", "2", ""],
        ["", "", "", "assert_text", "", "Sample Item", "Item appears in the grid"],
        [],
        ["Ledger list opens", "Ledger Master should open", "masters",
         "open_screen", "party", "", ""],
        ["", "", "", "assert_text", "", "Ledger Master", "Heading is visible"],
        [],
        ["Sale bill with one item", "Adding an item creates one line",
         "sales", "open_screen", "sale_bill", "", ""],
        ["", "", "", "set_party", "", "Cash Account", ""],
        ["", "", "", "add_item", "", "Sample Item | 2", "Item | qty | rate"],
        ["", "", "", "expect_lines", "", "1", "Grid has one line"],
        ["", "", "", "close_form", "", "", "Close without saving"],
    ]
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue()


def valid_targets() -> dict:
    """UI ke dropdown ke liye -- kya-kya likha ja sakta hai."""
    return {
        "screens": sorted(SCREENS.keys()),
        "fields": sorted(locators.all_keys()),
        "actions": ACTIONS,
    }


def normalise_action(raw: str) -> str:
    a = (raw or "").strip().lower()
    if a in ACTIONS:
        return a
    return ALIASES.get(a, a)


def parse_rows(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Sheet ki rows -> tests ki list. (tests, warnings)
    Galti par poora import fail nahi karte -- jo theek hai wo le lete hain
    aur baaki ki warning de dete hain. Tester ko ek-ek karke theek karna
    aasan rehta hai.
    """
    tests: list[dict] = []
    warns: list[str] = []
    cur: dict | None = None
    targets = valid_targets()

    for i, r in enumerate(rows, start=2):
        get = lambda k: (r.get(k) or "").strip()  # noqa: E731
        name = get("Test Name")

        if name:
            cur = {"name": name, "description": get("Description"),
                   "module": get("Module") or "general", "steps": []}
            tests.append(cur)

        action = normalise_action(get("Action"))
        if not action:
            continue
        if cur is None:
            warns.append(f"Row {i}: this step has no test above it — "
                         f"fill in 'Test Name' on the first row of each test")
            continue
        if action not in ACTIONS:
            warns.append(f"Row {i}: '{get('Action')}' is not a known action. "
                         f"Try one of: {', '.join(ACTIONS[:6])}...")
            continue

        target, value = get("Screen/Field"), get("Value")
        if action == "open_screen" and target and target not in targets["screens"]:
            warns.append(f"Row {i}: no screen called '{target}'. "
                         f"Did you mean: {_near(target, targets['screens'])}")
        if action in ("click", "fill", "select", "press") and target \
                and target not in targets["fields"]:
            warns.append(f"Row {i}: field '{target}' is not in the locator map. "
                         f"Did you mean: {_near(target, targets['fields'])}")

        step = {"action": action}
        if target:
            step["target"] = target
        if value:
            step["value"] = value
        if get("Expected"):
            step["note"] = get("Expected")
        cur["steps"].append(step)

    tests = [t for t in tests if t["steps"]]
    return tests, warns


def _near(word: str, options: list[str], n: int = 3) -> str:
    import difflib
    hits = difflib.get_close_matches(word, options, n=n, cutoff=0.4)
    return ", ".join(hits) if hits else "(no close match)"


def parse_csv(text: str) -> tuple[list[dict], list[str]]:
    return parse_rows(list(csv.DictReader(io.StringIO(text))))


def parse_xlsx(data: bytes) -> tuple[list[dict], list[str]]:
    try:
        from openpyxl import load_workbook
    except ImportError:
        return [], ["Reading .xlsx needs openpyxl: pip install openpyxl"]
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], ["The sheet is empty"]
    head = [str(h or "").strip() for h in rows[0]]
    dicts = [dict(zip(head, [("" if v is None else str(v)) for v in r]))
             for r in rows[1:]]
    return parse_rows(dicts)
