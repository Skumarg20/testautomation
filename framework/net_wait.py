"""
API ka jawab aane tak ruko -- fixed sleep ki jagah.

MargBooks har search par server ko call karta hai. Ab tak hum "2 second ruko"
jaisa andaza laga rahe the. Wo do tarah se galat hai:
  - internet dheema ho to 2 second kam pad jate hain -> jhootha FAIL
  - jawab 200ms me aa jaye to 1.8 second bekaar jaate hain -> suite dheemi

Ab hum chalti hui request ginte hain aur zero hone ka intezaar karte hain.
"""
from __future__ import annotations

import time

TRACK_JS = r"""
(() => {
  if (window.__mbNet) return;
  window.__mbNet = {inflight: 0, last: Date.now(), total: 0};

  const done = () => { window.__mbNet.inflight = Math.max(0, window.__mbNet.inflight - 1);
                       window.__mbNet.last = Date.now(); };
  const start = () => { window.__mbNet.inflight++; window.__mbNet.total++;
                        window.__mbNet.last = Date.now(); };

  const of = window.fetch;
  window.fetch = function (...a) {
    start();
    return of.apply(this, a).finally(done);
  };

  const open = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (...a) {
    this.addEventListener('loadstart', start);
    this.addEventListener('loadend', done);
    return open.apply(this, a);
  };
})();
"""


def arm(context):
    """Har page pe request counter laga do."""
    context.add_init_script(TRACK_JS)


def state(page) -> dict:
    try:
        return page.evaluate("() => window.__mbNet || {inflight:0,last:0,total:0}")
    except Exception:  # noqa: BLE001
        return {"inflight": 0, "last": 0, "total": 0}


def wait_quiet(page, quiet_ms: int = 500, timeout_ms: int = 15000,
               min_wait_ms: int = 150) -> dict:
    """
    Ruko jab tak koi API chal rahi ho, phir thoda aur (quiet_ms) taaki Angular
    grid dobara render kar le.

    Wapas deta hai: {'waited': ms, 'requests': kitni calls hui, 'timeout': bool}
    """
    t0 = time.time()
    page.wait_for_timeout(min_wait_ms)      # request shuru hone ka mauka do
    start_total = state(page).get("total", 0)

    while (time.time() - t0) * 1000 < timeout_ms:
        st = state(page)
        if st.get("inflight", 0) == 0:
            # aakhri jawab ko quiet_ms hue?
            try:
                idle = page.evaluate(
                    "() => Date.now() - (window.__mbNet ? window.__mbNet.last : 0)")
            except Exception:  # noqa: BLE001
                idle = quiet_ms
            if idle >= quiet_ms:
                return {"waited": int((time.time() - t0) * 1000),
                        "requests": st.get("total", 0) - start_total,
                        "timeout": False}
        page.wait_for_timeout(120)

    return {"waited": int((time.time() - t0) * 1000),
            "requests": state(page).get("total", 0) - start_total,
            "timeout": True}
