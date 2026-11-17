"""
ag-Grid padhne aur bharne wala hissa.

MargBooks ka item grid <table> NAHI hai -- wo ag-Grid hai, jo div se bana
hota hai:

    div[role="row"][row-index="0"]
      div[col-id="Product"]  div[col-id="batchName"]  div[col-id="unitToEnteredValue"]

Main ab tak `table tbody tr` dhoondh raha tha, isliye grid hamesha khali
milta tha aur `expect_lines` hamesha 0 deta tha.

Aur ek baat: grid ke input field ka number ROW ka hai, tab ka nahi --
    #txt-tmp_barcode-0        pehli row
    #txt-tmp_barcode-1        doosri row
Jabki header ke field tab ka number rakhte hain (txtLedgerName27).
Ek hi form me do alag naming -- ye jaane bina koi bhi automation atkegi.
"""
from __future__ import annotations

# Grid ke har column ka input -- {kaam: id ka shuruaati hissa}
CELL_IDS = {
    "barcode":  "txt-tmp_barcode",
    "item":     "txt-itemLinkID",
    "qty":      "txt-unitToEnteredValue",
    "rate":     "txt-salePurchaseRate",
    "discount": "txt-discount1",
    "discount2": "txt-discount2",
    "vol_disc": "txt-volumediscount",
    "vol_disc2": "txt-volumediscount2",
    "free":     "txt-freeQuantity",
    "batch":    "txt-batchName",
    "expiry":   "txt-expiryDate",
}

READ_JS = r"""
() => {
  const rows = [...document.querySelectorAll('[role="row"][row-index]')];
  const out = [];
  for (const r of rows) {
    const idx = parseInt(r.getAttribute('row-index'), 10);
    const cells = {};
    r.querySelectorAll('[col-id]').forEach(c => {
      const k = c.getAttribute('col-id');
      const t = (c.innerText || '').replace(/\s+/g, ' ').trim();
      if (k) cells[k] = t;
    });
    const filled = Object.entries(cells)
      .filter(([k]) => !['Action', 'action', ''].includes(k))
      .some(([, v]) => v.length > 0);
    out.push({index: idx, cells, filled});
  }
  out.sort((a, b) => a.index - b.index);
  return out;
}
"""

COLUMNS_JS = r"""
() => [...document.querySelectorAll('[role="columnheader"][col-id], .ag-header-cell[col-id]')]
        .map(h => ({id: h.getAttribute('col-id'),
                    label: (h.innerText || '').replace(/\s+/g,' ').trim()}))
        .filter(c => c.id)
"""


def rows(page) -> list[dict]:
    """Grid ki saari rows -- khali wali bhi (ag-Grid pehle se khali rows rakhta hai)."""
    try:
        return page.evaluate(READ_JS) or []
    except Exception:  # noqa: BLE001
        return []


def filled_rows(page) -> list[dict]:
    """Sirf wo rows jinme sach me data hai."""
    return [r for r in rows(page) if r["filled"]]


def line_count(page) -> int:
    return len(filled_rows(page))


def columns(page) -> list[dict]:
    """Grid me kaunse column hain -- trade ke hisaab se badalte hain."""
    try:
        return page.evaluate(COLUMNS_JS) or []
    except Exception:  # noqa: BLE001
        return []


def has_column(page, col_id: str) -> bool:
    return any(c["id"] == col_id for c in columns(page))


def cell_id(field: str, row: int = 0) -> str:
    """'qty', 0 -> '#txt-unitToEnteredValue-0'"""
    base = CELL_IDS.get(field)
    if not base:
        raise KeyError(f"Grid me '{field}' naam ka koi field nahi. "
                       f"Ye hain: {sorted(CELL_IDS)}")
    return f"#{base}-{row}"


def cell_exists(page, field: str, row: int = 0) -> bool:
    """Ye cell abhi maujood hai? (trade ke hisaab se column ho ya na ho)"""
    try:
        return page.locator(cell_id(field, row)).count() > 0
    except Exception:  # noqa: BLE001
        return False


def available_fields(page, row: int = 0) -> list[str]:
    """Is row me abhi kaunse field bhare ja sakte hain."""
    return [f for f in CELL_IDS if cell_exists(page, f, row)]


def cell_text(page, row: int, col_id: str) -> str:
    """Kisi row ke kisi column ka dikhne wala text."""
    try:
        return page.evaluate(
            """([i, c]) => {
                 const r = document.querySelector(`[role="row"][row-index="${i}"]`);
                 if (!r) return '';
                 const cell = r.querySelector(`[col-id="${c}"]`);
                 return cell ? (cell.innerText || '').replace(/\\s+/g,' ').trim() : '';
               }""", [row, col_id])
    except Exception:  # noqa: BLE001
        return ""
