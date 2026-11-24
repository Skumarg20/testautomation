"""
The test companies, one per trade, and the guard that keeps writes inside them.

Every company here was created for testing by this project (2026-11-18) on the user's approval. Saves,
deletes and Control Room changes are allowed ONLY when the header shows one of these companies; the user's
real companies stay read-only even when "Allow writes" is on.
"""
from __future__ import annotations

import re

from config.settings import settings

# business type id -> (trade, test company)
TRADES: dict[int, tuple[str, str]] = {
    5: ("chemist", "QA Chemist"),
    13: ("pharma", "QA Pharma Distribution"),
    3: ("billing", "QA Billing General"),
    17: ("grocery", "QA Grocery"),
    8: ("garment", "QA Garment"),
    12: ("mobile", "QA Mobile Trade"),
    19: ("computer", "QA Computer Hardware"),
    2: ("automobile", "QA Automobile"),
}
BY_TRADE = {t: c for t, c in TRADES.values()}
# GST-registered twins (UP, GSTIN given by the user on 2026-11-18): the companies above are GST Unregistered
# (locked), so tax is always 0 there; GST cases run in these.
GST_BY_TRADE = {t: c.replace("QA ", "QA GST ", 1) for t, c in BY_TRADE.items()}
TEST_COMPANIES = set(BY_TRADE.values()) | set(GST_BY_TRADE.values())


class NotATestCompany(RuntimeError):
    """A write was about to happen in a company that is not one of the QA test companies."""


def current(page) -> str:
    """Company name shown in the app header ('' when no company is open)."""
    try:
        txt = page.locator("#dropdownMenuLink, #txtheadercompname").first.inner_text(timeout=4000)
    except Exception:  # noqa: BLE001
        return ""
    name = " ".join(str(txt).split())
    m = re.match(r"(.+?)\s*\([^()]*\)\s*Books\b", name)        # "QA Chemist (QACH) Books From ..."
    return (m.group(1) if m else name).strip()


def is_test_company(name: str) -> bool:
    return name.strip() in TEST_COMPANIES


def require_test_company(page, what: str = "write") -> str:
    name = current(page)
    for _ in range(5):                      # the header is briefly empty while a screen loads: look again
        if name:
            break
        page.wait_for_timeout(1500)
        name = current(page)
    if not is_test_company(name):
        raise NotATestCompany(
            f"Refused to {what}: the open company is {name or '(none)'!r}, not a QA test company "
            f"({', '.join(sorted(TEST_COMPANIES))}). Real companies are read-only.")
    return name


def switch(page, name: str) -> None:
    """Open company `name` from the company list (exact, trimmed match) and check the header."""
    name = BY_TRADE.get(name.strip().lower(), name.strip())
    if current(page) == name:
        return
    page.goto(settings.BASE_URL + "/user-company", wait_until="domcontentloaded")
    cells = page.locator('[role=row] [col-id="compname"]')
    cells.first.wait_for(timeout=90000)
    page.wait_for_timeout(2000)
    # The company list is an ag-Grid: only the rows in view exist in the page, so scroll until the name shows.
    hits, texts = [], []
    for _ in range(40):
        texts = [" ".join(t.split()) for t in cells.all_inner_texts()]
        hits = [i for i, t in enumerate(texts) if t == name]
        if hits:
            break
        try:
            page.locator(".ag-body-viewport, .ag-center-cols-viewport").first.evaluate("e => e.scrollBy(0, 250)")
        except Exception:  # noqa: BLE001
            page.mouse.wheel(0, 250)
        page.wait_for_timeout(350)
    if len(hits) != 1:
        raise RuntimeError(f"{len(hits)} companies named exactly {name!r}")
    cells.nth(hits[0]).dblclick()
    page.wait_for_url(re.compile(r"/dashboard"), timeout=120000)
    got = ""
    for _ in range(12):                                   # the header fills in late on a slow server
        page.wait_for_timeout(5000)
        got = current(page)
        if got:
            break
    if got != name:
        raise RuntimeError(f"header shows {got!r} after switching to {name!r}")
