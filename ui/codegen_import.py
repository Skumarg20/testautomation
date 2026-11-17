"""
Playwright codegen se record kiya hua script yahan import karo.

KYUN
----
`npx playwright codegen` ya `playwright codegen` chala kar tester khud
MargBooks me kaam karta hai, aur Playwright uske har click/type ko script
me likh deta hai. Wo script yahan daal do -- hum usse test case bana denge.

Iska sabse bada faayda ye hai ki record karte waqt tester ASLI RAASTA leta
hai: wahi menu, wahi popup, wahi kram. Andaza kahin nahi lagta.

KYA NIKAALTE HAIN
-----------------
    page.goto(...)                       -> open_screen (menu se)
    page.click / .getByRole().click()    -> click
    page.fill(...)                       -> fill
    page.selectOption(...)               -> select
    page.press(...)                      -> press
    expect(...).toBeVisible()            -> assert_visible
    expect(...).toContainText('x')       -> assert_text

Python aur JavaScript dono tarah ki recording padh lete hain.

JO SAMAJH NA AAYE
-----------------
Us line par ANDAZA nahi lagate. Wo alag se dikha di jaati hai, taaki tester
khud dekh kar tay kare. Chupchaap aadha test bana dena, kuch na banane se
bura hai -- kyunki wo chalta rahega aur galat cheez check karta rahega.
"""
from __future__ import annotations

import re

from framework.screens import SCREENS

# URL -> screen ka naam (menu se kholne ke liye)
_URL2SCREEN = {}
for _k, _cfg in SCREENS.items():
    if _cfg.get("url"):
        _URL2SCREEN[_cfg["url"].rstrip("/")] = _k

# ---- ek line se kaam nikaalne wale patterns ----
# JS aur Python dono ka rehnuma: page.fill('sel', 'val') / page.fill("sel", "val")
_S = r"""['"]([^'"]*)['"]"""

PATTERNS = [
    ("goto",     re.compile(rf"\.goto\(\s*{_S}")),
    ("fill",     re.compile(rf"\.fill\(\s*{_S}\s*,\s*{_S}")),
    ("type",     re.compile(rf"\.type\(\s*{_S}\s*,\s*{_S}")),
    ("select",   re.compile(rf"\.select_option\(\s*{_S}\s*,\s*{_S}")),
    ("selectJs", re.compile(rf"\.selectOption\(\s*{_S}\s*,\s*{_S}")),
    ("press",    re.compile(rf"\.press\(\s*{_S}\s*,\s*{_S}")),
    ("click",    re.compile(rf"\.click\(\s*{_S}")),
    ("dblclick", re.compile(rf"\.dblclick\(\s*{_S}")),
]

# getByRole('button', { name: 'Save' }).click()
# JS:     getByRole('button', { name: 'Save' })
# Python: get_by_role("button", name="Save")
# Dono chalein -- tester jis bhi bhasha me record kare.
BY_ROLE = re.compile(
    rf"get_?[bB]y_?[rR]ole\(\s*{_S}\s*,\s*[{{(]?\s*name\s*[:=]\s*{_S}")
BY_LABEL = re.compile(rf"get_?[bB]y_?[lL]abel\(\s*{_S}")
BY_PH = re.compile(rf"get_?[bB]y_?[pP]laceholder\(\s*{_S}")
BY_TEXT = re.compile(rf"get_?[bB]y_?[tT]ext\(\s*{_S}")

EXPECT_VISIBLE = re.compile(r"toBeVisible|to_be_visible")
EXPECT_TEXT = re.compile(rf"(?:toContainText|to_contain_text|toHaveText|"
                         rf"to_have_text)\(\s*{_S}")

SKIP_LINE = re.compile(
    r"^\s*(//|#|import |from |const |let |var |async |await browser|"
    r"browser\.|context\.|def |class |@|\)|\}|\{|test\(|test\.|"
    r"page\s*=|context\s*=|browser\s*=)")


LOCATOR_CALL = re.compile(rf"\.locator\(\s*{_S}\s*\)")


def _locator_from(line: str) -> str | None:
    """
    Line me se locator nikaalo.

    Playwright do tarah likhta hai, aur codegen dono deta hai:
        page.fill('#id', 'val')              <- selector pehle argument me
        page.locator('#id').fill('val')      <- alag call me
    Pehle wale ko hi dekhna adhoora tha -- aadhi recording chhoot jati thi.
    """
    m = LOCATOR_CALL.search(line)
    if m:
        return m.group(1)
    m = BY_ROLE.search(line)
    if m:
        return f"role={m.group(1)}:{m.group(2)}"
    m = BY_LABEL.search(line)
    if m:
        return f"nearlabel={m.group(1)}"
    m = BY_PH.search(line)
    if m:
        return f"placeholder={m.group(1)}"
    m = BY_TEXT.search(line)
    if m:
        return f"text={m.group(1)}"
    return None


def _screen_for(url: str) -> str | None:
    """URL se screen ka naam -- taaki menu se khola ja sake."""
    path = re.sub(r"^https?://[^/]+", "", url).rstrip("/") or "/"
    if path in ("", "/"):
        return "dashboard"
    return _URL2SCREEN.get(path)


def parse(script: str) -> dict:
    """
    Recording -> steps.

    Wapas: {"steps": [...], "unknown": [...], "stats": {...}}
    """
    steps: list[dict] = []
    unknown: list[dict] = []
    seen_actions = 0

    for n, raw in enumerate(script.split("\n"), 1):
        line = raw.strip()
        if not line or SKIP_LINE.match(line):
            continue
        # Jaani-pehchani harkatein, ya koi bhi page.<kuch>() call.
        #
        # Pehle sirf jaani-pehchani harkatein dekhta tha, aur baaki lines
        # CHUPCHAAP chhoot jati thin. page.kuchBhi() bhi page ka hi kaam hai --
        # samajh na aaye to batana chahiye, chhupana nahi. Warna tester ko
        # lagega poori recording aa gayi, jabki aadhi reh gayi.
        known = any(w in line.lower() for w in
                    (".click(", ".fill(", ".goto(", ".press(", "select",
                     "expect", ".type(", ".dblclick(", ".check(", ".upload"))
        page_call = re.search(r"\bpage\s*\.\s*\w+\s*\(", line)
        if not known and not page_call:
            continue

        seen_actions += 1
        step = _one(line)
        if step:
            step["note"] = line[:110]
            steps.append(step)
        else:
            unknown.append({
                "line": n, "text": line[:110],
                "why": "Ye kaam samajh nahi aaya",
                "hint": "Step haath se jod do, ya recording ka wo hissa dobara karo",
            })

    return {"steps": steps, "unknown": unknown,
            "stats": {"lines_with_actions": seen_actions,
                      "converted": len(steps), "skipped": len(unknown)}}


def _one(line: str) -> dict | None:
    """Ek line -> ek step."""
    low = line.lower()

    # ---- assertions pehle, kyunki unme bhi locator hota hai ----
    if "expect" in low:
        m = EXPECT_TEXT.search(line)
        if m:
            return {"action": "assert_text", "value": m.group(1)}
        if EXPECT_VISIBLE.search(line):
            loc = _locator_from(line)
            first = re.search(rf"locator\(\s*{_S}", line)
            target = loc or (first.group(1) if first else None)
            if target:
                return {"action": "assert_visible", "target": target}
        return None

    # ---- goto -> menu se kholna ----
    m = re.search(rf"\.goto\(\s*{_S}", line)
    if m:
        screen = _screen_for(m.group(1))
        if screen:
            # URL se nahi, MENU se. Recording me URL hota hai, par asli user
            # menu se hi jata hai -- aur URL se jaane par page reload hota hai.
            return {"action": "open_screen", "target": screen}
        return None

    # ---- getBy* wale ----
    loc = _locator_from(line)

    for kind, pat in PATTERNS:
        m = pat.search(line)
        if not m:
            continue
        if kind == "goto":
            continue
        if kind in ("fill", "type"):
            return {"action": "fill", "target": loc or m.group(1),
                    "value": m.group(2)}
        if kind in ("select", "selectJs"):
            return {"action": "select", "target": loc or m.group(1),
                    "value": m.group(2)}
        if kind == "press":
            return {"action": "press", "target": loc or m.group(1),
                    "value": m.group(2)}
        if kind in ("click", "dblclick"):
            return {"action": "click", "target": loc or m.group(1)}

    # locator('x').fill('y') / getByRole(...).click() --
    # locator alag call me hai, action alag me
    if loc:
        if ".click(" in line:
            return {"action": "click", "target": loc}
        m = re.search(rf"\.fill\(\s*{_S}", line)
        if m:
            return {"action": "fill", "target": loc, "value": m.group(1)}
        m = re.search(rf"\.press\(\s*{_S}", line)
        if m:
            return {"action": "press", "target": loc, "value": m.group(1)}
    return None


def to_case(script: str, name: str, description: str = "",
            module: str = "") -> dict:
    """
    Recording se poora test case banao (abhi save nahi karte).

    module na diya ho (ya "general" ho) to steps dekh kar khud tay karte
    hain -- recording me pehla open_screen hi bata deta hai ki ye kis
    hisse ka test hai.
    """
    out = parse(script)
    guessed = _guess_module(out["steps"])
    return {"name": name, "description": description,
            "module": (module if module and module != "general" else guessed),
            "steps": out["steps"], "unknown": out["unknown"],
            "stats": out["stats"]}


def _guess_module(steps: list[dict]) -> str:
    from framework import menu_tree
    for st in steps:
        if st.get("action") == "open_screen":
            path = menu_tree.menu_of_screen(str(st.get("target", "")))
            if path:
                head = path.split(" > ")[0].lower()
                return {"master": "masters", "sale": "sales",
                        "purchase": "purchase", "stock management": "inventory",
                        "accounting trans.": "accounting"}.get(head, "general")
    return "general"
