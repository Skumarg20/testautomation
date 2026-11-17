"""
Virtual-scroll wala grid padhne ka sahi tareeka.

MargBooks ke list page virtual scrolling use karte hain: DOM me sirf wahi rows
hoti hain jo abhi screen pe dikh rahi hain. 80 ledger hone par bhi DOM me 20-25
hi milengi, aur scroll karne pe purani hat ke nayi aa jayengi.

Isliye do alag cheezein hain, aur inhe ghalat-malat karna hi meri pichhli
galti thi:

  visible_rows()  -> abhi screen pe jo dikh raha hai. "Sample Item dikh raha
                     hai ya nahi" jaise sawaal ke liye theek.
  total_count()   -> header ka "Total No of Ledgers: 80" label. Ye POORE data
                     ka sach batata hai aur filter karne pe badalta hai --
                     search ke test ke liye YAHI use karna chahiye.
  scroll_all()    -> scroll karke saari rows jama karo. Sahi par dheema; sirf
                     tab jab poori list chahiye ho.
"""
from __future__ import annotations

import re

ROWS_JS = r"""
(header) => {
  const norm = t => (t || '').replace(/\s+/g, ' ').trim();

  // 1. header cell -> uski row -> us row ka parent = rows ka container
  const leaves = [...document.querySelectorAll('th, td, div, span')]
    .filter(e => e.children.length === 0 && e.offsetHeight > 0);
  const hdr = leaves.find(e => norm(e.innerText) === header);
  if (!hdr) return {found: false, reason: `header '${header}' nahi mila`};

  const headRow = hdr.closest('tr') || hdr.closest('[role="row"]') || hdr.parentElement;
  if (!headRow) return {found: false, reason: 'header row nahi mila'};

  // data rows header row ke bhai ho sakti hain, ya kisi alag tbody me
  let containers = [];
  const table = hdr.closest('table');
  if (table) {
    containers = [...table.querySelectorAll('tbody')];
    if (!containers.length) containers = [table];
    // virtual scroll me data aksar ALAG table me hota hai (header table + body table)
    const near = table.parentElement ? [...table.parentElement.querySelectorAll('table')] : [];
    for (const t of near) if (t !== table) containers.push(...t.querySelectorAll('tbody'), t);
  }
  if (headRow.parentElement) containers.push(headRow.parentElement);

  const seen = new Set();
  const rows = [];
  for (const c of containers) {
    const rs = [...c.querySelectorAll('tr, [role="row"]')];
    for (const r of rs) {
      if (r === headRow) continue;
      const cells = [...r.querySelectorAll('td, [role="cell"], [role="gridcell"]')];
      if (!cells.length) continue;
      const vals = cells.map(c2 => norm(c2.innerText));
      const key = vals.join('|');
      if (!key.replace(/\|/g, '').trim()) continue;   // poori khali row
      if (seen.has(key)) continue;
      seen.add(key);
      rows.push(vals);
    }
  }
  return {found: true, rows, header};
}
"""

SCROLLER_JS = r"""
(header) => {
  const norm = t => (t || '').replace(/\s+/g, ' ').trim();
  const leaves = [...document.querySelectorAll('th, td, div, span')]
    .filter(e => e.children.length === 0);
  const hdr = leaves.find(e => norm(e.innerText) === header);
  if (!hdr) return null;
  // sabse nazdeeki scroll hone wala parent
  let n = hdr;
  for (let i = 0; n && i < 10; i++, n = n.parentElement) {
    if (n.scrollHeight > n.clientHeight + 20) {
      n.__mbScroll = true;
      n.setAttribute('data-mb-scroller', '1');
      return {tag: n.tagName.toLowerCase(), h: n.clientHeight, sh: n.scrollHeight};
    }
  }
  return null;
}
"""


class GridNotFound(RuntimeError):
    pass


def visible_rows(page, header: str) -> list[list[str]]:
    """Abhi DOM me jo rows hain. Virtual scroll ki wajah se ye poori list NAHI hai."""
    r = page.evaluate(ROWS_JS, header)
    if not r.get("found"):
        raise GridNotFound(
            f"Grid nahi mila (header={header!r}): {r.get('reason')}\n  URL: {page.url}"
        )
    return r["rows"]


def total_count(page, label_prefix: str) -> int | None:
    """
    Header ka 'Total No of Ledgers:80' / 'Total no of items: 1' padho.
    Filter lagane pe ye badalta hai -- isliye search ke test ka SAHI paimana yahi hai.
    """
    try:
        txt = page.get_by_text(label_prefix, exact=False).first.inner_text()
    except Exception:  # noqa: BLE001
        return None
    m = re.search(r"(\d+)", txt.replace(",", ""))
    return int(m.group(1)) if m else None


def scroll_all(page, header: str, max_scrolls: int = 40) -> list[list[str]]:
    """
    Scroll karke saari rows jama karo (virtual scroll ke liye).
    Dheema hai -- sirf tab use karo jab poori list chahiye.
    """
    info = page.evaluate(SCROLLER_JS, header)
    seen: dict[str, list[str]] = {}

    def grab():
        for row in visible_rows(page, header):
            seen.setdefault("|".join(row), row)

    grab()
    if not info:
        return list(seen.values())      # scroll hi nahi hota -- jitna mila utna

    for _ in range(max_scrolls):
        before = len(seen)
        page.evaluate("""() => {
            const el = document.querySelector('[data-mb-scroller="1"]');
            if (el) el.scrollTop = Math.min(el.scrollTop + el.clientHeight * 0.8,
                                            el.scrollHeight);
        }""")
        page.wait_for_timeout(450)
        grab()
        if len(seen) == before:
            break
    return list(seen.values())


# ---- App ke alert / toast message ----

NOT_FOUND_WORDS = (
    "not found", "no record", "no data", "no result", "nothing found",
    "record not found", "no item", "no ledger", "not exist", "nahi mila",
)

# "Not found" MargBooks me toast nahi, search bar ke NEECHE inline aata hai.
# Isliye toast ke saath poore page ka chhota text bhi dekhna padta hai.
ALERT_JS = r"""
() => {
  const sels = '.toast, [class*="toast"], .alert, [class*="alert"], '
             + '[class*="snack"], [class*="notify"], [role="alert"], '
             + '.swal2-popup, .modal, .no-data, [class*="empty"], '
             + '[class*="no-record"], [class*="notfound"], td, div, span, p';
  const out = [];
  document.querySelectorAll(sels).forEach(e => {
    if (!e.offsetHeight) return;
    // sirf CHHOTE text -- poore page ka dump nahi chahiye
    const t = (e.innerText || '').replace(/\s+/g, ' ').trim();
    if (t && t.length < 80 && e.children.length === 0) out.push(t);
  });
  return out;
}
"""


def visible_alerts(page) -> list[str]:
    """Abhi screen pe jo alert/toast/message dikh raha hai."""
    try:
        return page.evaluate(ALERT_JS) or []
    except Exception:  # noqa: BLE001
        return []


def has_not_found_alert(page) -> tuple[bool, str]:
    """
    App ne "not found" bola? (True, message)

    MargBooks ka asli message: "ZZQQ_NOPE_999 Not Found!" -- ek <p> me,
    search bar ke NEECHE (toast nahi).

    Pehle main element-by-element scan kar raha tha aur wo kabhi chalta kabhi
    nahi. Ab poore page ka text ek baar padh kar dekhte hain -- ye sabse seedha
    aur sabse pakka tareeka hai.
    """
    try:
        body = (page.inner_text("body") or "").lower()
    except Exception:  # noqa: BLE001
        return False, ""
    for w in NOT_FOUND_WORDS:
        idx = body.find(w)
        if idx >= 0:
            start = max(0, idx - 40)
            snippet = body[start:idx + len(w) + 10].replace("\n", " ").strip()
            return True, snippet
    return False, ""
