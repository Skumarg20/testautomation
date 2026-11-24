"""
Test store -- testers ke likhe test yahan rehte hain.

Har test ek YAML file me: testcases/saved/<id>.yaml
Ek hi format jo automation bhi padhti hai aur insaan bhi -- isliye UI se
banaya test wahi hai jo pytest se chalta hai. Do alag format rakhna hota to
dono kabhi sync me nahi rehte.
"""
from __future__ import annotations

import re
import time
import yaml
from pathlib import Path

from config.settings import ROOT
from framework.case_loader import load_all

SAVED = ROOT / "testcases" / "saved"
SAVED.mkdir(parents=True, exist_ok=True)


def slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip()).strip("_").upper()
    return (s or "TEST")[:40]


def new_id(name: str) -> str:
    base = f"TC_{slug(name)}"
    existing = {c.id for c in list_all()}
    if base not in existing:
        return base
    n = 2
    while f"{base}_{n}" in existing:
        n += 1
    return f"{base}_{n}"


def list_all() -> list:
    """Saare test -- builtin aur testers ke banaye, dono."""
    return load_all()


def as_dicts() -> list[dict]:
    from framework import logbook
    hist = logbook.load_history()["tests"]
    out = []
    for c in list_all():
        out.append({
            "id": c.id,
            "title": c.title,
            "module": c.module,
            "menu": c.menu or "(not linked to a menu)",
            "menu_id": c.menu_id,
            "priority": c.priority,
            "tags": c.tags or [],
            "breaks_session": "breaks_session" in (c.tags or []),
            "destructive": bool(c.destructive),
            "draft": bool(getattr(c, "draft", False)),
            "known_issue": bool(getattr(c, "known_issue", False)),
            "steps": len(c.steps),
            "expected": c.expected or [],
            "preconditions": c.preconditions or [],
            "file": c.source_file,
            "editable": c.source_file.startswith("saved") or "/" in c.source_file,
            # Pichhli baar kya hua -- disk se, taaki server restart par bhi rahe
            "last": (hist.get(c.id) or {}).get("last"),
            "runs": (hist.get(c.id) or {}).get("total", 0),
        })
    return sorted(out, key=lambda x: (x["module"], x["id"]))


PRIORITY = {"high": "p1", "medium": "p2", "low": "p3", "p1": "p1", "p2": "p2", "p3": "p3"}


def save(name: str, description: str, module: str, steps: list[dict],
         author: str = "", tags: list[str] | None = None,
         destructive: bool = False, case_id: str | None = None, created: str | None = None,
         priority: str = "p2") -> dict:
    """Naya test save karo (ya purana update karo). priority: p1/p2/p3 or High/Medium/Low."""
    if not name.strip():
        raise ValueError("Test name is required")
    if not steps:
        raise ValueError("Add at least one step")

    cid = case_id or new_id(name)
    case = {
        "id": cid,
        "module": module or "general",
        "title": name.strip(),
        "priority": PRIORITY.get(str(priority or "").strip().lower(), "p2"),
        "tags": tags or [],
        "destructive": destructive,
        "preconditions": [f"Created by {author or 'unknown'} | "
                          f"{created or time.strftime('%Y-%m-%d %H:%M')}"],
        "expected": [description.strip()] if description.strip() else [],
        "steps": steps,
    }
    path = SAVED / f"{cid}.yaml"
    path.write_text(yaml.safe_dump([case], sort_keys=False, allow_unicode=True),
                    encoding="utf-8")
    return {"id": cid, "file": str(path)}


def get(case_id: str):
    for c in list_all():
        if c.id == case_id:
            return c
    return None


def detail(case_id: str) -> dict | None:
    """Edit ke liye poora record -- jo bhara tha wahi wapas mile."""
    c = get(case_id)
    if not c:
        return None
    author = ""
    for pre in (c.preconditions or []):
        if pre.startswith("Created by "):
            author = pre.replace("Created by ", "").split("|")[0].strip()
            break
    return {
        "id": c.id, "title": c.title, "module": c.module,
        "description": (c.expected or [""])[0],
        "author": author,
        "tags": [t for t in (c.tags or []) if t != "breaks_session"],
        "destructive": bool(c.destructive),
        "steps": c.steps,
        # Sirf tester ke banaye test badle ja sakte hain. Built-in test
        # agle update me wapas aa jayenge aur badlav ud jayega -- isliye
        # unki copy banti hai, unhe overwrite nahi karte.
        "editable": c.source_file.startswith("saved"),
        "source": c.source_file,
    }


def as_spec(case_id: str) -> dict:
    """
    Test ko Playwright script ki tarah dikhao.

    Ye DIKHANE ke liye hai, chalane ke liye nahi. Chalane wala rasta YAML
    hi rehta hai, kyunki wahi safety guard, control-room jaanch, self-healing
    aur menu navigation se guzarta hai -- .spec.js file un sab ke bahar hoti.
    Ise dekh kar tester samajh sakta hai ki step ka matlab kya hai, aur
    dev ise apne debugging me use kar sakta hai.
    """
    c = get(case_id)
    if not c:
        return {"error": "test not found"}

    lines = [
        "// " + "=" * 66,
        f"//  {c.id} -- {c.title}",
        f"//  module: {c.module}" + (f"  |  menu: {c.menu}" if c.menu else ""),
        "//",
        "//  DHYAAN: ye dikhane ke liye hai. Asli run YAML se hota hai,",
        "//  kyunki wahi safety guard, control-room jaanch aur self-healing",
        "//  se guzarta hai. Ye script un sab ke bahar hai.",
        "// " + "=" * 66,
        "",
        "import { test, expect } from '@playwright/test';",
        "",
        f"test({c.title!r}, async ({{ page }}) => {{",
    ]
    for st in c.steps:
        lines.append("  " + _spec_line(st))
    lines += ["});", ""]
    return {"id": c.id, "title": c.title, "code": "\n".join(lines)}


def _spec_line(st: dict) -> str:
    a = st.get("action", "")
    t = st.get("target", "")
    v = st.get("value", "")
    note = st.get("note", "")
    tail = f"   // {note}" if note else ""

    if a == "open_screen":
        return f"await openScreen(page, {t!r});{tail}"
    if a == "open_menu":
        return f"await openMenu(page, {t!r});{tail}"
    if a == "click":
        return f"await page.locator({t!r}).click();{tail}"
    if a == "fill":
        return f"await page.locator({t!r}).fill({v!r});{tail}"
    if a == "select":
        return f"await page.locator({t!r}).selectOption({v!r});{tail}"
    if a == "press":
        return f"await page.locator({t!r}).press({v!r});{tail}"
    if a == "assert_text":
        return f"await expect(page.locator('body')).toContainText({v!r});{tail}"
    if a == "assert_no_text":
        return f"await expect(page.locator('body')).not.toContainText({v!r});{tail}"
    if a == "assert_visible":
        return f"await expect(page.locator({t!r})).toBeVisible();{tail}"
    if a == "sleep":
        return f"await page.waitForTimeout({int(float(v or 1)) * 1000});{tail}"
    if a == "note":
        return f"// {v or note}"
    # unche star ke kaam -- inka koi seedha Playwright roop nahi hota
    arg = ", ".join(repr(x) for x in (t, v) if x)
    return f"await {a}(page{', ' + arg if arg else ''});{tail}"


def delete(case_id: str) -> bool:
    """Sirf testers ke banaye test hat sakte hain, builtin nahi."""
    path = SAVED / f"{case_id}.yaml"
    if path.exists():
        path.unlink()
        return True
    return False
