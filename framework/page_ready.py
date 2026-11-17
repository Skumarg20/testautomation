"""
Page SACH ME taiyaar hai ya nahi -- ye tay karna.

MargBooks Angular app hai aur dheere load hota hai. Uska matlab ye hai ki
"page khul gaya" ke teen alag matlab hote hain, aur teeno alag waqt pe hote
hain:

    1. URL badal gaya                 <- turant
    2. HTML aa gaya                   <- kuch der baad
    3. Angular ne field bana diye     <- iske BAAD

Ab tak main (1) ya (2) par bharosa kar raha tha aur catalogue jaldi scan kar
leta tha -- aadhe field milte hi nahi the. Isliye ab (3) ka intezaar hota hai.

Teen cheezein ek saath dekhte hain:
    - koi API chal rahi hai kya           (net_wait)
    - loader / spinner dikh raha hai kya
    - DOM ab bhi badal raha hai kya       (element ginti sthir hui?)

Teeno shaant ho jayein, tab page taiyaar hai.
"""
from __future__ import annotations

import time

from framework import net_wait

# MargBooks aur aam Angular apps ke loader
SPINNER_SEL = (
    ".loader", ".loading", ".spinner", ".ngx-spinner-overlay",
    "[class*='loader']:not([class*='loaded'])", "[class*='spinner']",
    ".mat-progress-spinner", ".overlay-loader", "#loader",
)

COUNT_JS = """
() => ({
  els: document.querySelectorAll('input,select,textarea,button,[col-id]').length,
  text: (document.body ? document.body.innerText.length : 0),
})
"""

SPINNER_JS = """
(sels) => sels.some(s => {
  try {
    return [...document.querySelectorAll(s)].some(e => {
      const r = e.getBoundingClientRect();
      return r.width > 0 && r.height > 0
             && getComputedStyle(e).visibility !== 'hidden';
    });
  } catch (e) { return false; }
})
"""


def spinner_visible(page) -> bool:
    try:
        return bool(page.evaluate(SPINNER_JS, list(SPINNER_SEL)))
    except Exception:  # noqa: BLE001
        return False


def wait_ready(page, timeout_ms: int = 25000, stable_ms: int = 700,
               verbose: bool = False) -> dict:
    """
    Page taiyaar hone tak ruko.

    stable_ms = itni der tak DOM na badle, tab maana jayega ki ban chuka hai.

    Wapas: {'ready': bool, 'waited': ms, 'why': kis wajah se ruka/chala}
    """
    t0 = time.time()
    last = None
    stable_since = None
    why = "ok"

    while (time.time() - t0) * 1000 < timeout_ms:
        # 1. API chal rahi ho to ruko
        st = net_wait.state(page)
        if st.get("inflight", 0) > 0:
            stable_since = None
            why = "API chal rahi hai"
            page.wait_for_timeout(150)
            continue

        # 2. loader dikh raha ho to ruko
        if spinner_visible(page):
            stable_since = None
            why = "loader dikh raha hai"
            page.wait_for_timeout(200)
            continue

        # 3. DOM sthir hua?
        try:
            now = page.evaluate(COUNT_JS)
        except Exception:  # noqa: BLE001
            page.wait_for_timeout(200)
            continue

        if last is not None and now == last:
            if stable_since is None:
                stable_since = time.time()
            elif (time.time() - stable_since) * 1000 >= stable_ms:
                waited = int((time.time() - t0) * 1000)
                if verbose:
                    print(f"  [ready] {waited}ms me taiyaar "
                          f"({now['els']} elements)")
                return {"ready": True, "waited": waited, "why": "sthir",
                        "elements": now["els"]}
        else:
            stable_since = None
            why = "DOM abhi ban raha hai"

        last = now
        page.wait_for_timeout(150)

    waited = int((time.time() - t0) * 1000)
    if verbose:
        print(f"  [ready] {waited}ms me bhi shaant nahi hua ({why})")
    return {"ready": False, "waited": waited, "why": why,
            "elements": (last or {}).get("els", 0)}


def wait_for_field_count(page, minimum: int = 3, timeout_ms: int = 20000) -> bool:
    """
    Kam se kam itne field aa jayein, tab tak ruko.

    Ek create-form pe scan hua tha jab sirf 2 field bane the -- baaki 12
    catalogue me gaye hi nahi. Isliye ginti ki bhi ek seema.
    """
    t0 = time.time()
    while (time.time() - t0) * 1000 < timeout_ms:
        try:
            n = page.evaluate(
                "() => [...document.querySelectorAll('input,select,textarea')]"
                ".filter(e => e.offsetHeight > 0 && e.type !== 'hidden').length")
        except Exception:  # noqa: BLE001
            n = 0
        if n >= minimum:
            return True
        page.wait_for_timeout(250)
    return False
