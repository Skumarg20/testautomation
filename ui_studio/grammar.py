"""
Plain-language step grammar for Test Studio's Write screen.

One step per line, values in "quotes". Every line is checked against app memory
(ui_studio/memory.py): locally, instantly, with no AI and no tokens.

    Log in
    create sale bill
    enter date "16-11-2026"
    search party "Ajay"
    select party "Ajay"
    select item "dolo" with qty "2", rate "100", discount "10"
    save bill
    verify "Bill saved"
    wait 2 seconds
    create 500 sale bills with 50 items each, random party and random items

Also: Open Sale Bill / Enter 5 in Disc 1.% / Set Rate to 50 / Click Save / # note.
A line that does not match is never guessed: it is returned as status "bad"
with the reason and, where possible, a free suggestion from memory.
"""
from __future__ import annotations

import difflib
import re

from ui_studio import memory

MAX_BULK = 5000
KINDS = ("login", "open", "pick", "search", "item", "fill", "click", "verify", "wait", "bulk")
_Q = r'["“]([^"”]*)["”]'


def _lev_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def _dist(a: str, b: str) -> int:
    """Levenshtein distance."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


class Memory:
    """A read-only view over memory.build() with the lookups the grammar needs."""

    def __init__(self, data: dict | None = None):
        self.d = data or memory.build()
        self.screens = self.d["screens"]
        self.taught = self.d.get("taught", {})

    def find_screen(self, text: str) -> str | None:
        t = re.sub(r"\s+(screen|page|window)$", "", memory.norm(text))
        best = None
        for name, s in self.screens.items():
            for a in s["aliases"]:
                if t == a and (best is None or len(a) > len(best[1])):
                    best = (name, a)
        return best[0] if best else None

    def screen_suggestions(self, text: str, n: int = 3) -> list[str]:
        t = memory.norm(text)
        scored = sorted(((min(_dist(t, a) for a in s["aliases"] or [""]), name)
                         for name, s in self.screens.items() if s["fields"]))
        return [name for _, name in scored[:n]]

    def find_field(self, screen: str, term: str) -> dict:
        t = re.sub(r"\s*(field|box|button)$", "", re.sub(r"^the\s+", "", memory.norm(term)))
        ta = self.taught.get(f"{screen}::{t}")
        fields = (self.screens.get(screen) or {}).get("fields", [])
        if ta:
            f = next((x for x in fields if x["name"] == ta["field"]), None)
            if f:
                return {"f": f, "learned": True}
        f = next((x for x in fields if t in x["aliases"] or memory.norm(x["name"]) == t), None)
        if f:
            return {"f": f}
        cand = []
        for x in fields:
            d = min(_dist(t, a) for a in (x["aliases"] + [memory.norm(x["name"])]))
            cand.append((d, x))
        cand.sort(key=lambda p: p[0])
        limit = max(2, len(t) // 3)
        near = [x["name"] for d, x in cand if d <= limit][:3]
        other = next((n for n, s in self.screens.items()
                      if n != screen and any(t in x["aliases"] for x in s["fields"])), None)
        return {"near": near, "other": other}


def _field_out(f: dict) -> dict:
    return {"name": f["name"], "sel": f["sel"], "xpath": f.get("xpath", ""), "kind": f["kind"], "stab": f["stab"]}


def _ok(**kw) -> dict:
    return {"status": "ok", **kw}


def _bad(note: str, **kw) -> dict:
    return {"status": "bad", "note": note, **kw}


def _field_step(M: Memory, ctx: dict, term: str, kind: str, value=None) -> dict:
    if not ctx.get("screen"):
        return _bad("Open a screen first",
                    why="Which screen should this happen on? Add a line like “Open Sale Bill” above.",
                    sugg=["Open Sale Bill", "Open Purchase Bill"])
    r = M.find_field(ctx["screen"], term)
    if r.get("f"):
        f = r["f"]
        out = _ok(kind=kind, screen=ctx["screen"], field=_field_out(f), learned=bool(r.get("learned")),
                  note=f["name"] + (f" = {value}" if value is not None else ""))
        if value is not None:
            out["value"] = value
        return out
    why = (f"“{term}” is on {r['other']}, not on {ctx['screen']}." if r.get("other")
           else f"{ctx['screen']} has no field called “{term}”.")
    return _bad(f"“{term}” not found", why=why, term=term, fixes=r.get("near", []), screen=ctx["screen"])


def _open(M: Memory, ctx: dict, screen: str) -> dict:
    ctx["screen"] = screen
    return _ok(kind="open", screen=screen, route=M.screens[screen]["route"], note=screen,
               screen_key=M.screens[screen]["key"])


def parse(line: str, ctx: dict, M: Memory | None = None) -> dict:
    M = M or Memory()
    rn = re.sub(r"\s+", " ", re.sub(r"[.!?]+$", "", line.strip()))
    t = rn.lower()
    if not t:
        return {"status": "empty"}
    if t.startswith(("#", "//")):
        return {"status": "note"}

    if re.fullmatch(r"(log ?in|login|sign in)( to the app| karo)?", t):
        ctx["screen"] = None
        return _ok(kind="login", note="User from Settings")

    m = re.search(r"(create|make|add)\s+(\d[\d,]*)\s+(sale\s+)?(bills?|invoices?)", t)
    if m:
        n = int(m.group(2).replace(",", ""))
        it = re.search(r"(\d+)\s+items?", t)
        if n > MAX_BULK:
            return _bad("Too many bills", why=f"Max {MAX_BULK:,} bills per run. Split it into smaller runs.")
        scr = M.find_screen("sale bill")
        if not scr:
            return _bad("Sale Bill is not in app memory", why="Run “Learn the app” first.")
        ctx["screen"] = scr
        return _ok(kind="bulk", screen=scr, count=n, items=int(it.group(1)) if it else 5,
                   note=f"{n} bills × {it.group(1) if it else '1–5'} items, random")

    m = re.fullmatch(r"(create|new|make|add)\s+(a\s+|new\s+)?(.+)", t)
    if m and M.find_screen(m.group(3)):
        return _open(M, ctx, M.find_screen(m.group(3)))

    m = re.fullmatch(r"(save|close)(\s+(the\s+)?(bill|invoice|entry|it))?", t)
    if m:
        return _field_step(M, ctx, m.group(1), "click")

    m = re.fullmatch(rf"(enter|type|put|write|fill)\s+(.+?)\s+{_Q}", rn, re.I)
    if m:
        return _field_step(M, ctx, m.group(2), "fill", m.group(3))
    m = re.fullmatch(rf"(search|find)\s+(.+?)\s+{_Q}", rn, re.I)
    if m:
        return _field_step(M, ctx, m.group(2), "search", m.group(3))

    m = re.fullmatch(rf"(select|choose|pick)\s+(.+?)\s+{_Q}\s*(with\s+(.+))?", rn, re.I)
    if m:
        term, val = m.group(2), m.group(3)
        if not re.fullmatch(r"(item|product)", term, re.I):
            return _field_step(M, ctx, term, "pick", val)
        r = _field_step(M, ctx, "product", "item", val)
        if r["status"] != "ok":
            return r
        r["extras"] = []
        for mm in re.finditer(rf"([A-Za-z][\w .%\-]*?)\s*{_Q}", m.group(5) or ""):
            key = re.sub(r"^(and|with)\s+", "", mm.group(1).strip(" ,"), flags=re.I).strip()
            fr = M.find_field(ctx["screen"], key)
            if not fr.get("f"):
                return _bad(f"“{key}” not found",
                            why=f"{ctx['screen']} has no field called “{key}”.",
                            term=key, fixes=fr.get("near", []), screen=ctx["screen"])
            r["extras"].append({"field": _field_out(fr["f"]), "value": mm.group(2)})
        r["note"] = val + (" · " + ", ".join(f"{x['field']['name']} {x['value']}" for x in r["extras"])
                           if r["extras"] else "")
        return r

    m = re.fullmatch(r"(open|go to|goto)\s+(the\s+)?(.+)", t) or re.fullmatch(r"()()(.+?)\s+kholo", t)
    if m:
        s = M.find_screen(m.group(3))
        if s:
            return _open(M, ctx, s)
        return _bad(f"Screen “{m.group(3)}” not found", why="This screen is not in app memory.",
                    sugg=["Open " + n for n in M.screen_suggestions(m.group(3))])

    m = re.fullmatch(r"(select|choose|pick)\s+(the\s+)?(party|customer|supplier|ledger)\s*:?\s*(.+)", rn, re.I)
    if m:
        return _field_step(M, ctx, "party", "pick", m.group(4).strip())

    m = re.fullmatch(r"add\s+(item|product)\s*:?\s*(.+)", rn, re.I)
    if m:
        v = m.group(2).strip()
        q = re.search(r"qty\s*(\d+)", v, re.I)
        r = _field_step(M, ctx, "product", "item", re.sub(r",?\s*qty\s*\d+", "", v, flags=re.I).strip())
        if r["status"] == "ok":
            r["qty"] = int(q.group(1)) if q else 1
            r["note"] = f"{r['value']} × {r['qty']}"
        return r

    m = re.fullmatch(r"(enter|type|put|write)\s+(.+?)\s+(in|into)\s+(the\s+)?(.+)", rn, re.I)
    if m:
        return _field_step(M, ctx, m.group(5), "fill", m.group(2).strip().strip('"“”'))
    m = re.fullmatch(r"(set|change|make)\s+(the\s+)?(.+?)\s+(to|=|as)\s+(.+)", rn, re.I)
    if m:
        return _field_step(M, ctx, m.group(3), "fill", m.group(5).strip())
    m = re.fullmatch(r"(click|press|tap)\s+(on\s+)?(the\s+)?(.+)", t)
    if m:
        return _field_step(M, ctx, m.group(4), "click")

    m = re.fullmatch(r"(verify|check|expect)\s*:?\s*(that\s+)?(.+)", rn, re.I) \
        or re.fullmatch(r"()()(.+?)\s+should\s+(appear|be visible|show)", rn, re.I)
    if m:
        w = m.group(3).strip().strip('"“”')
        return _ok(kind="verify", screen=ctx.get("screen"), what=w, note="Check: " + w)
    m = re.fullmatch(r"wait\s+(\d+)\s*(s|sec|secs|seconds?)", t)
    if m:
        return _ok(kind="wait", secs=int(m.group(1)), note=f"Wait {m.group(1)} s")

    return _bad("Line not understood", why="This line does not match any known step pattern.", ai=True)


def parse_all(lines: list[str], M: Memory | None = None) -> tuple[list[dict], dict]:
    M = M or Memory()
    ctx: dict = {"screen": None}
    out = []
    for ln in lines:
        before = ctx.get("screen")
        r = parse(ln, ctx, M)
        r["before"] = before
        out.append(r)
    return out, ctx


def palette(screen: str | None, M: Memory | None = None) -> list[str]:
    """Insert-chips for the screen currently open in the steps."""
    M = M or Memory()
    s = M.screens.get(screen) if screen else None
    if not s:
        names = [n for n, x in M.screens.items() if x["fields"]]
        base = ["Log in"] + [f"open {n.lower()}" for n in names if n in ("Sale Bill", "Purchase Bill", "Sale Bill List")][:3]
        return base + ['verify "Bill saved"'] if names else ["Log in"]
    first = ["Party Name", "Ledger Name", "Product", "Bill Date", "Bill No.", "Save", "Close"]
    rank = lambda f: (first.index(f["name"]) if f["name"] in first else len(first), -f.get("seen", 0))  # noqa: E731
    chips = []
    for f in sorted(s["fields"], key=rank):
        if f["kind"] == "button":
            if f["name"] in ("Save", "Close"):
                chips.append("save bill" if f["name"] == "Save" else "click close")
        elif f["name"] in ("Party Name", "Ledger Name"):
            chips.append('select party "Ajay"')
        elif f["name"] == "Product":
            chips.append('select item "dolo" with qty "2", rate "100", discount "10"')
        elif f["kind"] in ("input", "date"):          # dropdowns are Control Room settings, not typed into
            chips.append(f'enter {f["aliases"][0]} "…"')
    chips.append('verify "Bill saved"')
    seen, out = set(), []
    for c in chips:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out[:10]


def check(lines: list[str]) -> dict:
    M = Memory()
    results, ctx = parse_all(lines, M)
    ok = sum(1 for r in results if r["status"] == "ok")
    bad = sum(1 for r in results if r["status"] == "bad")
    return {"results": results, "ok": ok, "bad": bad, "palette": palette(ctx.get("screen"), M),
            "screen": ctx.get("screen")}


# ------------------------------------------------------------ YAML steps

def to_steps(lines: list[str]) -> list[dict]:
    """Written lines -> steps the project's StepRunner runs. Raises if any line is red."""
    M = Memory()
    results, _ = parse_all(lines, M)
    steps: list[dict] = []
    for ln, r in zip(lines, results):
        if r["status"] in ("empty", "note"):
            continue
        if r["status"] == "bad":
            raise ValueError(f"Line not mapped: {ln.strip()}")
        k, note = r["kind"], ln.strip()
        f = r.get("field")
        if k == "login":
            steps.append({"action": "note", "value": "Log in (the runner signs in before every test)", "note": note})
        elif k == "open":
            steps.append({"action": "open_screen", "target": r["screen_key"], "note": note})
        elif k == "pick" and f["name"] in ("Party Name", "Ledger Name"):
            steps.append({"action": "set_party", "value": r["value"], "note": note})
        elif k == "search" and f["name"] in ("Party Name", "Ledger Name"):
            continue          # typing the party is part of the pick; never type it twice
        elif k in ("pick", "search", "fill"):
            steps.append({"action": "fill", "target": f["sel"], "value": r["value"], "note": note})
        elif k == "item":
            cols = {x["field"]["name"]: x["value"] for x in r.get("extras", [])}
            qty = cols.get("Qty", r.get("qty", ""))
            parts = [r["value"], str(qty), str(cols.get("Rate", "")), str(cols.get("Disc 1.%", ""))]
            while parts and parts[-1] == "":
                parts.pop()
            steps.append({"action": "add_item", "value": " | ".join(parts), "note": note})
        elif k == "click":
            if f["name"] == "Save":
                steps.append({"action": "save_form", "note": note})
            elif f["name"] == "Close":
                steps.append({"action": "close_form", "note": note})
            else:
                steps.append({"action": "click", "target": f["sel"], "note": note})
        elif k == "verify":
            steps.append({"action": "assert_text", "value": r["what"], "note": note})
        elif k == "wait":
            steps.append({"action": "sleep", "value": str(r["secs"]), "note": note})
        elif k == "bulk":
            steps.append({"action": "bulk_sale_bills", "value": f"{r['count']} | {r['items']}", "note": note,
                          "destructive": True})
    return steps
