"""
MargBooks ke lookup field bharne ka ASLI tareeka.

Main ab tak field me naam TYPE kar raha tha. Wo galat hai. Asli tareeka:

    field pe click  ->  SPACE dabao  ->  #SearchBox wala popup khulta hai
    ->  usme naam type karo  ->  list me se row pe click

Isi wajah se placeholder me likha rehta hai "Press SpaceBar" -- app khud
bata raha tha aur maine dhyaan nahi diya.

Yahi tareeka Party, Patient Name, MR -- teeno ke liye hai.
"""
from __future__ import annotations

from framework import safety
from framework.base_page import BasePage

SEARCH_BOX = "input#SearchBox"
# popup ki list me option -- ag-Grid bhi ho sakti hai, simple div bhi
# Options are looked for INSIDE the open popup first: the bill's own grid also has [col-id] cells.
OPTION_SELECTORS = (
    'ngb-modal-window [col-id="LedgerName"]', 'ngb-modal-window [col-id="ledgerName"]', 'ngb-modal-window [col-id="Name"]',
    'ngb-modal-window [col-id="Product"]', 'ngb-modal-window [role="row"] [col-id]',
    '.modal.show [role="row"] [col-id]', '[col-id="LedgerName"]', '[col-id="Name"]',
)


class LookupFailed(RuntimeError):
    pass


def pick(bp: BasePage, field_locator, value: str, what: str = "value",
         timeout_ms: int = 8000) -> str:
    """
    Lookup field bharo: Space -> search -> option pe click.

    Wapas deta hai: jo option chuna gaya uska text.
    """
    page = bp.page
    safety.dismiss_modal(page)

    try:
        page.mouse.move(900, 300)           # the side menu expands under the mouse and can cover the form
    except Exception:  # noqa: BLE001
        pass
    box = page.locator(SEARCH_BOX).first
    already = False
    try:
        already = box.is_visible()           # the party list may open by itself on a new bill
    except Exception:  # noqa: BLE001
        pass
    if not already:
        safety.guarded_click(field_locator, f"lookup:{what}")
        page.wait_for_timeout(300)
        field_locator.press("Space")
        page.wait_for_timeout(500)
    try:
        box.wait_for(state="visible", timeout=timeout_ms)
    except Exception as e:  # noqa: BLE001
        # Kuch trade me lookup popup aata hi nahi -- seedha type hota hai.
        # Us soorat me seedha bhar do, error mat do.
        try:
            safety.safe_clear(field_locator, page)
            field_locator.type(value, delay=50)
            bp.settle()
            field_locator.press("Enter")
            bp.settle()
            return value
        except Exception:  # noqa: BLE001
            raise LookupFailed(
                f"'{what}' ke liye na search popup aaya na seedha type hua: {e}"
            ) from e

    safety.guarded_click(box, f"lookup.search:{what}", inside_modal=True)
    safety.safe_clear(box, page)
    box.type(value, delay=60)
    bp.settle()
    page.wait_for_timeout(600)

    chosen = _click_option(bp, value)
    if not chosen:
        raise LookupFailed(
            f"'{value}' lookup list me nahi mila ({what}).\n"
            f"  Ya to ye naam maujood nahi, ya spelling alag hai."
        )
    bp.settle()
    return chosen


def _click_option(bp: BasePage, value: str) -> str | None:
    """List me se matching row pe click. Pehla match hi lete hain."""
    page = bp.page
    low = value.lower()

    for sel in OPTION_SELECTORS:
        try:
            loc = page.locator(sel)
            n = min(loc.count(), 40)
            for i in range(n):
                cell = loc.nth(i)
                txt = (cell.inner_text() or "").strip()
                if txt and low in txt.lower():
                    if not cell.is_visible():
                        continue
                    safety.guarded_click(cell, f"option:{txt[:20]}", timeout=4000, inside_modal=True)
                    page.wait_for_timeout(400)
                    if page.locator(SEARCH_BOX).first.is_visible():   # a click only highlighted the row
                        page.keyboard.press("Enter")
                    return txt
        except Exception:  # noqa: BLE001
            continue

    # aakhri koshish: seedha text se
    try:
        opt = page.get_by_text(value, exact=False).first
        opt.wait_for(state="visible", timeout=2500)
        safety.guarded_click(opt, f"option:{value[:20]}", timeout=3000, inside_modal=True)
        if page.locator(SEARCH_BOX).first.is_visible():
            page.keyboard.press("Enter")
        return value
    except Exception:  # noqa: BLE001
        return None


def skip(bp: BasePage, field_locator):
    """Field ko chhod kar aage badho (Enter). Optional field ke liye."""
    try:
        field_locator.press("Enter")
        bp.page.wait_for_timeout(250)
    except Exception:  # noqa: BLE001
        pass
