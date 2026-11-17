"""
Saadhi bhasha se test steps banane wala.

Tester likhta hai:
    Item list kholo
    Search me "Sample Item" likho
    "Sample Item" dikhna chahiye

Aur ye ban jata hai:
    open_screen  item
    fill         item.search   Sample Item
    assert_text                Sample Item

DESIGN KA FAISLA -- AI yahan JAAN-BOOJH KAR nahi hai:

Ye parser niyam-aadharit hai, AI-aadharit nahi. Teen wajah:
  1. Ye har baar bilkul EK JAISA natija deta hai. Test ka matlab hi bharosa hai.
     Agar aaj "search me likho" se ek step bane aur kal doosra, to test bekaar.
  2. Paisa nahi lagta aur internet ke bina chalta hai.
  3. Jo samajh na aaye, wo CHUPCHAAP andaza nahi lagata -- saaf keh deta hai
     "ye line samajh nahi aayi" aur milta-julta naam suggest karta hai.

AI (agar API key ho) sirf un lines ke liye lagta hai jo parser chhod de --
aur uska natija bhi tester ko dikhaya jata hai, seedha save nahi hota.
"""
from __future__ import annotations

import difflib
import re

from framework.locator_store import store as locators
from framework.screens import SCREENS

# ---------------------------------------------------------------- intents
#
# Har intent ke wo shabd jo tester asal me likhta hai -- English aur Hinglish
# dono, kyunki dono chalte hain office me.

INTENTS: list[tuple[str, list[str]]] = [
    # Transaction form ke unche star ke kaam -- ye pehle aane chahiye, warna
    # "party set karo" me se "set" nikal kar galat intent ban jayega.
    ("set_party", [
        "party set karo", "set party", "party chuno", "party name daalo",
        "customer set karo", "party me", "bill kis party ka",
    ]),
    ("add_barcode", [
        "barcode se", "barcode daalo", "add barcode", "scan karo", "scan",
    ]),
    ("add_item", [
        "item jodo", "add item", "item daalo", "product jodo",
        "line jodo", "bill me item",
    ]),
    ("fill_header", [
        "header bharo", "poora header", "fill header", "details bharo",
    ]),
    ("pick_batch", [
        "batch chuno", "pick batch", "batch select",
    ]),
    ("expect_trade", [
        "trade hona chahiye", "pharma trade", "general trade", "wholesale trade",
        "trade check",
    ]),
    ("expect_field", [
        "field hona chahiye", "field maujood", "should have field",
    ]),
    ("expect_column", [
        "column hona chahiye", "grid me column", "should have column",
    ]),
    ("set_bill_discount", [
        "bill discount", "discount lagao", "discount daalo",
    ]),
    ("close_form", [
        "bill band karo", "form band karo", "close bill", "close form",
        "bina save band",
    ]),
    ("expect_lines", [
        "line honi chahiye", "lines honi chahiye", "kitni line",
    ]),
    ("open_menu", [
        "menu se kholo", "menu me jao", "open menu", "from menu",
    ]),
    ("open_screen", [
        "kholo", "khol", "open", "go to", "jao", "navigate to", "visit",
        "screen", "page kholo", "par jao", "pe jao",
    ]),
    ("fill", [
        "likho", "type", "enter", "bharo", "fill", "daalo", "dalo", "input",
        "write", "put",
    ]),
    ("select", [
        "chuno", "select", "choose", "dropdown se", "pick",
    ]),
    ("click", [
        "click", "dabao", "press", "tap", "dabana", "button dabao", "click on",
    ]),
    ("assert_no_text", [
        "nahi dikhna chahiye", "should not see", "should not appear",
        "nahi aana chahiye", "must not show", "nahi hona chahiye",
    ]),
    ("assert_text", [
        "dikhna chahiye", "should see", "should show", "should appear",
        "aana chahiye", "verify", "check that", "must show", "dikhe",
        "hona chahiye", "expect",
    ]),
    ("sleep", [
        "ruko", "wait", "pause", "intezaar", "thoda ruk",
    ]),
    ("press", [
        "key dabao", "press key", "keyboard", "enter dabao", "esc dabao",
    ]),
]

# ------------------------------------------------------- screen ke aam naam

SCREEN_WORDS: dict[str, list[str]] = {
    "item": ["item list", "item master", "items", "item", "product list",
             "stock list", "item screen"],
    "party": ["ledger", "ledger master", "party", "party master", "party list",
              "ledger list", "customer list", "supplier list"],
    "sale_bill": ["sale bill", "new sale", "sale invoice", "billing", "sale entry",
                  "naya bill", "sale bill banao"],
    "sale_list": ["sale list", "sale bill list", "bill list", "sales list"],
    "sale_return": ["sale return", "credit note", "return bill"],
    "purchase_bill": ["purchase bill", "new purchase", "purchase entry",
                      "purchase invoice"],
    "purchase_list": ["purchase list", "purchase bill list"],
    "purchase_return": ["purchase return", "debit note"],
    "receipt": ["receipt", "receipt voucher"],
    "payment": ["payment", "payment voucher"],
    "journal": ["journal", "journal entry"],
    "credit_note": ["credit note voucher"],
    "debit_note": ["debit note voucher"],
    "stock_transfer": ["stock transfer", "transfer stock"],
    "physical_stock": ["physical stock", "stock count"],
    "dashboard": ["dashboard", "home", "main screen"],
    "counter_sale": ["counter sale", "pos", "retail sale"],
    "group": ["group", "account group"],
    "store": ["store", "godown", "warehouse"],
    "agency": ["agency", "company master", "manufacturer"],
    "salt": ["salt"],
    "hsn": ["hsn", "hsn sac", "sac"],
    "unit": ["unit", "uom"],
    "price_list": ["price list", "rate master"],
}

# --------------------------------------------- field ke aam naam (screen wise)
#
# "search me likho" ka matlab kis screen pe ho, ye us waqt ke screen se tay
# hota hai. Isliye parser chalte-chalte yaad rakhta hai ki abhi kaunsi screen
# khuli hai.

FIELD_WORDS: dict[str, list[str]] = {
    "search":       ["search", "search box", "search bar", "khoj", "dhoondho"],
    "new_btn":      ["create", "create f2", "new", "add new", "naya", "plus",
                     "create button"],
    "party":        ["party name", "party", "customer name", "ledger name field"],
    "name":         ["name", "naam", "description", "item name"],
    "gstin":        ["gstin", "gst number", "gst no"],
    "mobile":       ["mobile", "phone", "mobile number"],
    "save_btn":     ["save", "save button", "f10", "save karo"],
    "bill_no":      ["bill no", "bill number", "invoice no", "invoice number"],
    "date":         ["date", "bill date", "tareekh"],
    "bill_discount": ["bill discount", "discount"],
    "search_by":    ["search by", "search type"],
    "store":        ["store", "godown"],
    "profile":      ["profile", "profile icon", "user icon", "avatar"],
    "logout":       ["logout", "log out", "sign out"],
}

ACTIONS_NEEDING_TARGET = {"open_screen", "click", "fill", "select", "press"}
# Inhe target nahi chahiye -- ye poore form pe lagte hain
NO_TARGET = {"open_menu", "set_party", "add_item", "add_barcode", "fill_header", "pick_batch",
             "set_bill_discount", "close_form", "save_form", "expect_total",
             "expect_trade", "expect_field", "expect_column"}
ACTIONS_NEEDING_VALUE = {"fill", "select", "assert_text", "assert_no_text",
                         "press", "sleep", "wait_text"}


# ---------------------------------------------------------------- helpers

def _quoted(line: str) -> str | None:
    """Quotes ke andar ka text -- tester aksar value ko quote karta hai."""
    m = re.search(r"[\"'“”‘’]([^\"'“”‘’]{1,80})[\"'“”‘’]", line)
    return m.group(1).strip() if m else None


def _match_intent(line: str) -> tuple[str | None, str]:
    """
    Line ka intent dhoondho. Lambe phrase pehle dekhte hain, warna
    "dikhna chahiye" me se "dikhe" pehle match ho jayega aur galat intent milega.
    """
    low = " " + line.lower().strip() + " "
    best: tuple[str | None, str, int] = (None, "", 0)
    for action, words in INTENTS:
        for w in words:
            if re.search(rf"(^|\W){re.escape(w)}(\W|$)", low) and len(w) > best[2]:
                best = (action, w, len(w))
    return best[0], best[1]


def _match_screen(line: str) -> tuple[str | None, str]:
    low = line.lower()
    best: tuple[str | None, str, int] = (None, "", 0)
    for screen, words in SCREEN_WORDS.items():
        if screen not in SCREENS:
            continue
        for w in words:
            if w in low and len(w) > best[2]:
                best = (screen, w, len(w))
    return best[0], best[1]


def _match_field(line: str, screen: str | None) -> tuple[str | None, str]:
    """Field ka naam -- abhi khuli screen ke hisaab se."""
    low = line.lower()
    known = set(locators.all_keys())
    page = _locator_page(screen)

    best: tuple[str | None, str, int] = (None, "", 0)
    for field, words in FIELD_WORDS.items():
        for w in words:
            if w in low and len(w) > best[2]:
                best = (field, w, len(w))
    field, word, _ = best
    if not field:
        return None, ""

    for candidate in (f"{page}.{field}" if page else None,
                      f"nav.{field}", f"item.{field}", f"party.{field}",
                      f"sale.{field}"):
        if candidate and candidate in known:
            return candidate, word
    return None, word


def _locator_page(screen: str | None) -> str | None:
    """Screen ka naam -> locators file me uska page prefix."""
    if not screen:
        return None
    if screen in ("item", "party"):
        return screen
    if screen.startswith(("sale", "purchase", "counter")):
        return "sale"
    return None


def _near(word: str, options, n: int = 3) -> str:
    hits = difflib.get_close_matches(word, list(options), n=n, cutoff=0.35)
    return ", ".join(hits) if hits else "(no close match)"


# ---------------------------------------------------------------- parser

def parse(text: str) -> dict:
    """
    Plain text -> {steps, issues, module}

    issues = un lines ki list jo samajh nahi aayin. In par chupchaap andaza
    NAHI lagate -- tester ko dikhate hain, kyunki galat step chupke se save
    ho jana isse kahin bura hai.
    """
    steps: list[dict] = []
    issues: list[dict] = []
    screen: str | None = None

    lines = [l.strip(" -•\t") for l in re.split(r"[\n;]+", text or "")]
    lines = [l for l in lines if l.strip()]

    for n, line in enumerate(lines, 1):
        action, word = _match_intent(line)
        value = _quoted(line)

        if not action:
            issues.append({
                "line": n, "text": line,
                "why": "Could not tell what to do on this line.",
                "hint": "Try: 'Open item list', 'Type \"abc\" in search', "
                        "'Should see \"abc\"'",
            })
            continue

        step: dict = {"action": action, "note": line}

        if action == "open_screen":
            sc, _w = _match_screen(line)
            if not sc:
                issues.append({
                    "line": n, "text": line,
                    "why": "Could not tell which screen to open.",
                    "hint": f"Did you mean: {_near(line, SCREENS.keys())}",
                })
                continue
            screen = sc
            step["target"] = sc

        elif action in NO_TARGET:
            if action == "close_form":
                pass                       # value ki zaroorat nahi
            elif not value:
                # add_item ke liye quotes ke bina bhi chalne do: "Sample Item | 2"
                tail = re.split(rf"\b{re.escape(word)}\b", line, flags=re.I)[-1]
                value = tail.strip(" ,.:-")
                if not value:
                    issues.append({
                        "line": n, "text": line,
                        "why": "Value nahi mili.",
                        "hint": ('Item jodne ke liye: Add item "Sample Item | 2"'
                                 if action == "add_item"
                                 else 'Value quotes me likho'),
                    })
                    continue
            if value:
                step["value"] = value

        elif action in ("fill", "select", "click", "press"):
            fld, w = _match_field(line, screen)
            if not fld:
                issues.append({
                    "line": n, "text": line,
                    "why": f"Could not find a field called '{w or line}'."
                           + ("" if screen else " Open a screen first."),
                    "hint": f"Did you mean: {_near(w or line, locators.all_keys())}",
                })
                continue
            step["target"] = fld
            if action in ("fill", "select", "press"):
                if not value:
                    issues.append({
                        "line": n, "text": line,
                        "why": "No value found to type.",
                        "hint": 'Put the value in quotes: Type "Sample Item" in search',
                    })
                    continue
                step["value"] = value

        elif action in ("assert_text", "assert_no_text"):
            if not value:
                # quote nahi hai to intent wale shabd ke pehle ka hissa lo
                head = re.split(rf"\b{re.escape(word)}\b", line, flags=re.I)[0]
                value = head.strip(" ,.:-")
            if not value:
                issues.append({
                    "line": n, "text": line,
                    "why": "No text found to check for.",
                    "hint": 'Put it in quotes: Should see "Sample Item"',
                })
                continue
            step["value"] = value

        elif action == "expect_lines":
            m = re.search(r"(\d+)", line)
            if not m:
                issues.append({"line": n, "text": line,
                               "why": "Kitni line honi chahiye, ye number nahi mila.",
                               "hint": "Aise likho: 1 line honi chahiye"})
                continue
            step["value"] = m.group(1)

        elif action == "sleep":
            m = re.search(r"(\d+)", line)
            step["value"] = m.group(1) if m else "2"

        steps.append(step)

    module = _module_for(screen)
    return {"steps": steps, "issues": issues, "module": module,
            "screen": screen}


def _module_for(screen: str | None) -> str:
    if not screen:
        return "general"
    cfg = SCREENS.get(screen, {})
    menu = cfg.get("menu") or ""
    return {"master": "masters", "sale": "sales", "purchase": "purchase",
            "accounting": "accounting", "stock": "inventory"}.get(menu, "general")


def parse_with_ai(text: str) -> dict:
    """
    Pehle niyam, phir AI.

    Niyam-parser jo samajh le wo AI ko bhejte hi nahi -- wo hissa hamesha ek
    jaisa rehta hai aur muft hai. AI sirf BACHI HUI lines ke liye chalta hai,
    aur uska jawab bhi tester ko dikhaya jata hai, chupchaap save nahi hota.
    """
    base = parse(text)
    if not base["issues"]:
        return {**base, "ai_used": False, **_mapped(base)}

    from framework import ai
    if not ai.available()["active"]:
        return {**base, "ai_used": False,
                "ai_note": "AI key set nahi hai -- Settings me GEMINI_API_KEY daalo"}

    leftover = "\n".join(i["text"] for i in base["issues"])
    try:
        out = ai.text_to_steps(leftover, sorted(SCREENS.keys()),
                               locators.all_keys())
    except ai.AIError as e:
        return {**base, "ai_used": False, "ai_note": str(e)}

    ai_steps = out.get("steps") or []
    for st in ai_steps:
        st["from_ai"] = True          # UI me alag rang -- tester dekh kar maane

    still = [{"line": u.get("line", ""), "text": u.get("line", ""),
              "why": u.get("why", "AI bhi nahi samjha"),
              "hint": "Line dobara likho, ya step haath se jodo"}
             for u in (out.get("unknown") or [])]

    merged = base["steps"] + ai_steps
    return {
        "steps": merged,
        "issues": still,
        "module": base["module"] or out.get("module", "general"),
        "screen": base.get("screen"),
        "ai_used": bool(ai_steps),
        "ai_count": len(ai_steps),
        **_mapped({"steps": merged, "screen": base.get("screen")}),
    }


def _mapped(base: dict) -> dict:
    """
    Har step ka target asli element se joda gaya ya nahi -- aur kitne
    bharose ke saath.

    Ye tester ko SAVE SE PEHLE dikhaya jata hai. Baad me fail hone se
    pehle bata dena hamesha behtar hai.
    """
    try:
        from framework import mapping
        return {"mapping": mapping.map_steps(base.get("steps") or [],
                                             screen=base.get("screen") or "")}
    except Exception:  # noqa: BLE001
        return {}


def examples() -> list[str]:
    """UI me dikhane ke liye -- tester ko format samajh aa jaye."""
    return [
        "Sale bill kholo",
        'Party set karo "Cash Account"',
        'Add barcode "80000111 | 2"',
        "1 line honi chahiye",
        "Bill band karo",
        "",
        "Open item list",
        'Type "Sample" in search',
        "Wait 2 seconds",
        'Should see "Sample"',
        "",
        "Sale bill kholo",
        'Party set karo "Cash Account"',
        'Add item "Sample Item | 2"',
        "1 line honi chahiye",
        "Bill band karo",
    ]
