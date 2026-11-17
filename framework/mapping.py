"""
Tester ke shabd se ASLI element -- bharose ke number ke saath.

KYUN YE ALAG HISSA HAI
----------------------
Sabse khatarnak cheez jo ye tool kar sakta hai, wo hai CHUPCHAAP GALAT
element chun lena. Test chalega, hara dikhega, aur galat cheez jaanchta
rahega. Fail hona usse behtar hai -- fail dikhta to hai.

Isliye har mapping ke saath ek number aata hai:

    0.90 - 1.00   pakka          -- seedha use karo
    0.75 - 0.89   theek-thaak    -- use karo, par report me likho
    0.75 se neeche kuch nahi     -- "nahi mila" kaho aur vikalp dikhao

Aur ek niyam jo toda nahi jata: **selector kabhi banate nahi.**
Wo ya to scanner se aata hai, ya browser me dekhe hue registry se, ya
tester ke likhe locators se. AI se selector kabhi nahi -- AI sirf ye
samajhne ke liye hai ki tester kehna kya chah raha hai.
"""
from __future__ import annotations

import difflib
import re

HIGH = 0.90
OK = 0.75

# Jahan-jahan se element mil sakta hai, aur unpe kitna bharosa hai.
# Haath se likhe locators sabse upar: unhe kisi insaan ne dekh kar likha hai.
SOURCE_WEIGHT = {
    "yaml": 1.00,        # locators/margbooks.yaml
    "registry": 0.95,    # browser me khud dekha hua
    "metadata": 0.90,    # source code se nikala hua
}


def _tokens(text: str) -> list[str]:
    t = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(text or ""))
    words = re.findall(r"[a-z0-9]+", t.lower())
    # Ye shabd naam ka hissa nahi, sirf uski kism batate hain.
    # "save button" aur "save_btn" ek hi cheez hain -- dono taraf se ye
    # shabd hatane par hi wo baat samajh aati hai.
    NOISE = {"txt", "btn", "button", "input", "field", "box", "ng", "the", "a"}
    return [w for w in words if w not in NOISE]


# "one" -> "1" jaisi baatein, kyunki tester dono likhta hai
WORD_NUM = {"one": "1", "two": "2", "three": "3", "first": "1", "second": "2",
            "ek": "1", "do": "2", "teen": "3"}


def _normalise(tokens: list[str]) -> list[str]:
    return [WORD_NUM.get(t, t) for t in tokens]


def score(phrase: str, candidate: str) -> float:
    """
    Do naam kitne milte hain -- 0 se 1 ke beech.

    Sirf akshar milane se kaam nahi chalta: "Discount 1" aur "Discount 2"
    me 90% akshar ek jaise hain, par wo do alag field hain. Isliye pehle
    SHABD milate hain, aur number ko alag se wazan dete hain.
    """
    want = _normalise(_tokens(phrase))
    have = _normalise(_tokens(candidate))
    if not want or not have:
        return 0.0

    if want == have:
        return 1.0

    common = set(want) & set(have)
    if not common:
        return 0.0

    # Number alag ho to ye bilkul alag field hai -- Discount 1 vs Discount 2
    want_nums = {t for t in want if t.isdigit()}
    have_nums = {t for t in have if t.isdigit()}
    if want_nums and have_nums and want_nums != have_nums:
        return 0.0

    overlap = len(common) / max(len(set(want)), len(set(have)))
    # sab shabd mil gaye par kram/extra shabd alag hain
    if set(want) <= set(have):
        overlap = max(overlap, 0.88)

    # akshar-star ka milaan bhi thoda jodte hain
    ratio = difflib.SequenceMatcher(
        None, " ".join(want), " ".join(have)).ratio()
    return round(min(1.0, overlap * 0.75 + ratio * 0.25), 3)


class Match:
    """Ek mapping ka natija -- aur uska bharosa."""

    def __init__(self, phrase: str, selectors: list[str], label: str,
                 confidence: float, source: str, alternatives=None):
        self.phrase = phrase
        self.selectors = selectors
        self.label = label
        self.confidence = round(confidence, 3)
        self.source = source
        self.alternatives = alternatives or []

    @property
    def resolved(self) -> bool:
        return bool(self.selectors) and self.confidence >= OK

    @property
    def level(self) -> str:
        if self.confidence >= HIGH:
            return "pakka"
        if self.confidence >= OK:
            return "theek"
        return "kam"

    def as_dict(self) -> dict:
        return {
            "requested": self.phrase, "matched": self.label,
            "confidence": self.confidence, "level": self.level,
            "source": self.source, "resolved": self.resolved,
            "selector": self.selectors[0] if self.selectors else None,
            "selectors": self.selectors,
            "alternatives": self.alternatives,
        }


def unresolved(phrase: str, alternatives: list[str] | None = None) -> Match:
    return Match(phrase, [], "", 0.0, "none", alternatives)


def resolve(phrase: str, kind: str = "any", screen: str = "") -> Match:
    """
    Teeno jagah dhoondho, sabse achha jawab lo.

    Kahin bhi kaafi bharosa na mile to KHALI Match lautate hain -- uske saath
    milte-julte naam bhi, taaki tester khud chun sake. Andaza lagana yahan
    sabse bura vikalp hai.
    """
    best: Match | None = None
    seen: list[tuple[float, str, str]] = []

    for src, rows in (("yaml", _from_yaml(phrase)),
                      ("registry", _from_registry(phrase, kind, screen)),
                      ("metadata", _from_metadata(phrase, kind))):
        for label, sels, raw in rows:
            conf = raw * SOURCE_WEIGHT[src]
            seen.append((conf, label, src))
            if best is None or conf > best.confidence:
                best = Match(phrase, sels, label, conf, src)

    seen.sort(key=lambda x: -x[0])
    alts = [f"{lab} ({int(c * 100)}%, {s})" for c, lab, s in seen[1:4]]

    if best is None or not best.resolved:
        return unresolved(phrase, [f"{lab} ({int(c * 100)}%)"
                                   for c, lab, _ in seen[:4]])
    best.alternatives = alts
    return best


# ---------------------------------------------------------------- sources

def _from_yaml(phrase: str) -> list[tuple[str, list[str], float]]:
    from framework.locator_store import store
    out = []
    for key in store.all_keys():
        tail = key.split(".")[-1].replace("_", " ")
        s = max(score(phrase, tail), score(phrase, key.replace(".", " ")))
        if s > 0.5:
            try:
                out.append((key, list(store.candidates(key)), s))
            except Exception:  # noqa: BLE001
                continue
    return out


def _from_registry(phrase: str, kind: str,
                   screen: str) -> list[tuple[str, list[str], float]]:
    from framework import catalogue
    data = catalogue.load()["screens"]
    screens = [screen] if screen and screen in data else list(data)
    out = []
    for sc in screens:
        for key, el in (data.get(sc) or {}).items():
            if el.get("danger"):
                continue
            if kind != "any" and el.get("kind") not in (kind, "select"):
                continue
            name = el.get("label") or el.get("placeholder") or el.get("id") or key
            s = score(phrase, name)
            if s > 0.5:
                sels = [f["sel"] for f in (el.get("fallbacks") or [])] or \
                       ([el["css"]] if el.get("css") else [])
                if sels:
                    out.append((f"{name} [{sc}]", sels, s))
    return out


def _from_metadata(phrase: str, kind: str) -> list[tuple[str, list[str], float]]:
    from framework import code_scanner
    rows = code_scanner.load().get("elements", {})
    out = []
    for key, el in rows.items():
        if re.search(r"del(ete)?|remove|trash", key, re.I):
            continue
        if kind != "any" and el.get("kind") not in (kind, "select"):
            continue
        name = el.get("label") or el.get("placeholder") or el.get("id") or key
        s = score(phrase, name)
        if s > 0.5 and el.get("selectors"):
            out.append((f"{name} [{el.get('file', 'source')}]",
                        el["selectors"], s))
    return out


# ---------------------------------------------------------------- plan

def map_steps(steps: list[dict], screen: str = "") -> dict:
    """
    Poore test ke har step ka target mapping -- confidence ke saath.

    Wapas: {"mappings": [...], "unresolved": [...], "lowest": 0.0}

    Ye UI me dikhaya jata hai TEST SAVE HONE SE PEHLE, taaki tester dekh
    sake ki kis field pe bharosa kam hai. Baad me fail hone se pehle bata
    dena hamesha behtar hai.
    """
    TYPE_ACTIONS = {"fill", "type"}
    CLICK_ACTIONS = {"click", "press"}

    mappings, weak = [], []
    for i, st in enumerate(steps, 1):
        target = st.get("target")
        action = st.get("action", "")
        if not target or action in ("open_screen", "open_menu", "goto", "note"):
            continue
        kind = ("type" if action in TYPE_ACTIONS
                else "click" if action in CLICK_ACTIONS else "any")
        m = resolve(target, kind=kind, screen=screen)
        row = {"step": i, "action": action, **m.as_dict()}
        mappings.append(row)
        if not m.resolved:
            weak.append(row)

    lowest = min([m["confidence"] for m in mappings], default=1.0)
    return {"mappings": mappings, "unresolved": weak, "lowest": lowest}
