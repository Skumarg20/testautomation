"""
App memory for Test Studio: which screens and fields the tool knows.

Built from what the project already learned (locators/locators_registry.json,
written by the crawler and every run), plus the screen list in
framework/screens.py, plus the words testers have taught (config/studio_aliases.json).
Nothing is invented: a field is in memory only if the crawler saw it, or it is
a known grid column of a billing screen (pages/ag_grid.CELL_IDS).
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

from config.settings import ROOT

ALIASES_FILE = ROOT / "config" / "studio_aliases.json"
_lock = threading.Lock()
_cache: dict = {"stamp": None, "data": None}

# Words a tester naturally uses for the common fields (merged with what the screen shows).
SEED_ALIASES = {
    "party name": ["party", "customer", "supplier", "ledger", "party name"],
    "ledger name": ["ledger", "name", "ledger name"],
    "bill no.": ["bill no", "bill number", "invoice no", "invoice number"],
    "bill date": ["date", "bill date"],
    "save": ["save", "f10", "save button"],
    "save as draft": ["draft", "save as draft", "save draft"],
    "close": ["close", "esc", "close button"],
    "bill discount": ["bill discount", "bill disc"],
    "search": ["search", "search box", "search bar"],
    "mobile": ["mobile", "phone", "mobile number"],
}

GRID_FIELDS = [  # name, CELL_IDS key, aliases
    ("Product", "item", ["product", "item", "item name", "barcode"]),
    ("Qty", "qty", ["qty", "quantity", "unit-1", "unit 1"]),
    ("Free", "free", ["free", "free qty"]),
    ("Rate", "rate", ["rate", "price"]),
    ("Disc 1.%", "discount", ["disc", "discount", "disc 1", "disc 1%", "disc 1.%", "disc1"]),
    ("Disc 2.%", "discount2", ["disc 2", "disc 2%", "disc 2.%", "disc2"]),
    ("Batch", "batch", ["batch", "batch no"]),
    ("Expiry", "expiry", ["expiry", "expiry date", "exp"]),
]
_BAD_LABELS = {"", "dashboard", "×", "₹", "x"}
_TITLE_FIX = {"party": "Ledger Master", "item": "Item Master", "party_create": "Ledger Create",
              "item_create": "Item Create", "sale_list": "Sale Bill List",
              "purchase_list": "Purchase Bill List"}


def norm(s: str) -> str:
    """lower-case, single spaces, no trailing punctuation."""
    return re.sub(r"\s+", " ", str(s or "").lower().replace("“", '"').replace("”", '"')).strip(" .!?")


def humanize(s: str) -> str:
    s = re.sub(r"^(txt|btn|chk|ddl)[-_]?(?=[A-Za-z])", "", s or "")
    s = re.sub(r"\d+$", "", s).replace("_", " ").replace("-", " ")
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s).strip()
    return " ".join(w[:1].upper() + w[1:] for w in s.split())


def screen_title(key: str) -> str:
    return _TITLE_FIX.get(key) or key.replace("_", " ").title()


def _kind(el: dict) -> str:
    tag, typ = el.get("tag", ""), el.get("type", "")
    if tag == "select":
        return "select"
    if tag == "button" or el.get("kind") == "click" and tag != "input":
        return "button"
    if typ == "checkbox":
        return "check"
    if re.search(r"date", (el.get("id", "") + el.get("fcn", "")).lower()):
        return "date"
    if tag == "a":
        return "link"
    return "input"


def _locator(el: dict) -> tuple[str, int, dict]:
    """(primary selector, stability 0-100, details). Stable ids beat text beat position."""
    fcn, eid, name = el.get("fcn", ""), el.get("id", ""), el.get("name", "")
    ph, css = el.get("placeholder", ""), el.get("css", "")
    seen = min(int(el.get("seen", 1)), 10)
    loc = {"fcn": fcn, "id": eid, "css": css, "xpath": el.get("xpath", "")}
    if fcn:
        return f'[formcontrolname="{fcn}"]', min(99, 94 + seen // 4), loc
    if eid:
        stem = re.sub(r"\d+$", "", eid)
        if stem != eid:      # Angular appends a tab number: txtLedgerName44
            return f'[id^="{stem}"]', 78, loc
        return f"#{eid}", min(98, 90 + seen // 3), loc
    if name:
        return f'[name="{name}"]', 80, loc
    if ph:
        return f'[placeholder="{ph}"]', 62, loc
    return css, 40, loc


def _load_taught() -> dict:
    try:
        return json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def teach(term: str, screen: str, field: str) -> None:
    if not all(isinstance(x, str) for x in (term, screen, field)):
        raise ValueError("term, screen and field must be text")
    term = norm(term)
    if not term or not screen or not field:
        raise ValueError("term, screen and field are required")
    scr = build()["screens"].get(screen)
    if not scr:
        raise ValueError(f"App memory has no screen called “{screen}”.")
    if not any(f["name"] == field for f in scr["fields"]):
        raise ValueError(f"The screen “{screen}” has no field called “{field}” in app memory.")
    with _lock:
        d = _load_taught()
        d[f"{screen}::{term}"] = {"screen": screen, "field": field, "term": term,
                                   "at": time.strftime("%Y-%m-%d %H:%M")}
        ALIASES_FILE.parent.mkdir(parents=True, exist_ok=True)
        ALIASES_FILE.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
        _cache["stamp"] = None


def untaught(term: str, screen: str) -> bool:
    """Remove a word that was taught wrongly. True when it was there."""
    if not isinstance(term, str) or not isinstance(screen, str):
        raise ValueError("term and screen must be text")
    key = f"{screen}::{norm(term)}"
    with _lock:
        d = _load_taught()
        if key not in d:
            return False
        d.pop(key)
        ALIASES_FILE.parent.mkdir(parents=True, exist_ok=True)
        ALIASES_FILE.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
        _cache["stamp"] = None
    return True


def taught() -> dict:
    return _load_taught()


def _screen_words() -> dict[str, list[str]]:
    try:
        from ui.nl import SCREEN_WORDS
        return SCREEN_WORDS
    except Exception:  # noqa: BLE001
        return {}


def _registry() -> dict:
    from framework import catalogue
    return catalogue.load().get("screens", {})


def build(force: bool = False) -> dict:
    """The whole memory. Cached until the registry or taught words change."""
    from framework import catalogue
    stamps = tuple(p.stat().st_mtime if p.exists() else 0 for p in (catalogue.FILE, ALIASES_FILE))
    if not force and _cache["stamp"] == stamps and _cache["data"]:
        return _cache["data"]
    try:
        from framework.screens import SCREENS
    except Exception:  # noqa: BLE001
        SCREENS = {}
    try:
        from pages.ag_grid import CELL_IDS
    except Exception:  # noqa: BLE001
        CELL_IDS = {}
    words, reg, screens = _screen_words(), _registry(), {}

    for key in sorted(set(SCREENS) | set(reg)):
        cfg = SCREENS.get(key, {})
        title = screen_title(key)
        aliases = {norm(title), key.replace("_", " ")} | {norm(w) for w in words.get(key, [])}
        fields: dict[str, dict] = {}
        for el in (reg.get(key) or {}).values():
            if el.get("danger"):
                continue
            label = (el.get("label") or "").strip()
            fcn, eid = el.get("fcn", ""), el.get("id", "")
            if el.get("name") == "SearchBox":
                name = "Global Search"
            elif label and norm(label) not in _BAD_LABELS and len(label) <= 40:
                name = label
            elif fcn:
                name = humanize(fcn)
            elif eid:
                name = humanize(eid)
            elif el.get("placeholder"):
                name = el["placeholder"]
            else:
                continue
            if not name or len(name) > 40 or name.lower().startswith(("my-tabs", "controlroom")):
                continue
            # Rows of data the crawler happened to see (a party's edit button, a bare number) are not fields.
            if re.fullmatch(r"[\d\s.,:/-]*", name) or (eid or "").startswith(("Gridedit", "grid-edit")):
                continue
            sel, stab, loc = _locator(el)
            if not sel:
                continue
            kind = _kind(el)
            als = {norm(name)}
            for x in (humanize(fcn), humanize(eid)):
                if x:
                    als.add(norm(x))
            als |= {norm(a) for a in SEED_ALIASES.get(norm(name), [])}
            row = {"name": name, "aliases": sorted(a for a in als if a), "kind": kind, "stab": stab,
                   "sel": sel, "xpath": loc["xpath"], "loc": loc, "seen": int(el.get("seen", 1))}
            old = fields.get(norm(name))
            if not old or (stab, row["seen"]) > (old["stab"], old["seen"]):
                fields[norm(name)] = row
        if key.startswith(("sale_", "purchase_", "counter")) and key not in ("sale_list", "sale_draft") \
                or cfg.get("plus"):
            for gname, cell, gal in GRID_FIELDS:
                base = CELL_IDS.get(cell)
                if not base:
                    continue
                fields.setdefault(norm(gname), {
                    "name": gname, "aliases": sorted({norm(gname), *gal}), "kind": "grid", "stab": 85,
                    "sel": f'[id^="{base}-"]', "xpath": "", "seen": 0,
                    "loc": {"fcn": "", "id": f"{base}-0", "css": f'[id^="{base}-"]', "xpath": ""}})
        screens[title] = {"key": key, "aliases": sorted(a for a in aliases if a),
                          "route": cfg.get("url") or "", "fields": sorted(fields.values(), key=lambda f: f["name"])}

    t = _load_taught()
    for ent in t.values():
        s = screens.get(ent["screen"])
        if s:
            for f in s["fields"]:
                if f["name"] == ent["field"]:
                    f.setdefault("taught", []).append(ent["term"])
    n_fields = sum(len(s["fields"]) for s in screens.values())
    learned = time.strftime("%d-%b-%Y", time.localtime(catalogue.FILE.stat().st_mtime)) \
        if catalogue.FILE.exists() and n_fields else None
    data = {"learned_on": learned, "trade": _trade(), "screens": screens, "taught": t}
    _cache.update(stamp=stamps, data=data)
    return data


def _trade() -> str:
    try:
        from framework import control_room
        d = control_room.load()
        return str(d.get("trade") or d.get("business_type") or "")
    except Exception:  # noqa: BLE001
        return ""


def stats() -> dict:
    m = build()
    scr = [s for s in m["screens"].values() if s["fields"]]
    return {"learned_on": m["learned_on"], "screens": len(scr),
            "fields": sum(len(s["fields"]) for s in scr), "trade": m["trade"]}


def rows(screen: str = "", q: str = "") -> dict:
    m, q = build(), norm(q)
    out = []
    for sname, s in m["screens"].items():
        if screen and sname != screen:
            continue
        for f in s["fields"]:
            tw = f.get("taught", [])
            if q and not (q in norm(f["name"]) or any(q in a for a in f["aliases"] + tw)):
                continue
            out.append({"screen": sname, "field": f["name"], "kind": f["kind"], "stab": f["stab"],
                        "loc": {"primary": f["sel"], "fcn": f["loc"]["fcn"], "id": f["loc"]["id"],
                                "css": f["loc"]["css"], "xpath": f["loc"]["xpath"]},
                        "aliases": f["aliases"][:6], "taught": tw})
    names = sorted(n for n, s in m["screens"].items() if s["fields"])
    return {"screens": names, "rows": out[:1500], "total": len(out)}
