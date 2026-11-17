"""
Element catalogue -- agent ki apni yaaddasht.

KYA KARTA HAI
-------------
Jab bhi koi screen khulti hai, agent uske SAARE field aur button scan karta
hai aur unka poora pata likh leta hai: id, CSS selector, XPath, paas ka label,
placeholder, formcontrolname. Ye sab locators/catalogue.json me save hota hai.

Agli baar jab tester likhega "Item Name me 'Paracetamol' likho", to agent
catalogue me se "Item Name" dhoondh kar uska CSS/XPath nikal lega -- chahe wo
field pehle kabhi use hua ho ya nahi.

KYUN ZAROORI HAI
----------------
Ab tak main har field ka locator HAATH se likh raha tha, aur har naye page pe
atak jata tha:
    item.name -> 'txtitemname' try kiya, asli me 'txtItemName' nikla
Ye kaam aadmi ka nahi hai. Agent ek baar page dekh le, to use sab pata hona
chahiye.

NIYAM JO TODE NAHI JATE
-----------------------
1. Delete/remove wale element catalogue me jate hain par "khatarnak" mark ke
   saath -- taaki galti se bhi na chunein.
2. Ek hi phrase ke do matlab ho to bharosa (score) kam kar dete hain aur
   dono dikhate hain -- chupchaap ek chun lena galat hai.
3. Catalogue sirf BADHTA hai. Purani entry tab hi hatti hai jab wo screen pe
   kai baar na mile -- ek run ki galti se saara gyaan nahi mitna chahiye.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

from config.settings import ROOT

FILE = ROOT / "locators" / "locators_registry.json"
# Purana naam -- ek baar apne aap uthaa lete hain, taaki seekha hua gyaan
# naam badalne se na ude
_OLD_FILE = ROOT / "locators" / "catalogue.json"
_lock = threading.Lock()

DANGER = re.compile(r"(del(ete)?|trash|remove|discard|destroy|erase)", re.I)

# Har screen ke elements scan karne wala JS.
# Har element ka CSS aur XPath dono banate hain -- CSS tez hai, XPath tab kaam
# aata hai jab element ki koi apni pehchan na ho.
SCAN_JS = r"""
() => {
  const norm = t => (t || '').replace(/\s+/g, ' ').trim();

  const cssPath = (el) => {
    if (el.id && /^[A-Za-z][\w-]*$/.test(el.id))
      return `${el.tagName.toLowerCase()}#${el.id}`;
    const fcn = el.getAttribute('formcontrolname');
    if (fcn) return `${el.tagName.toLowerCase()}[formcontrolname="${fcn}"]`;
    const nm = el.getAttribute('name');
    if (nm) return `${el.tagName.toLowerCase()}[name="${nm}"]`;
    const ph = el.getAttribute('placeholder');
    if (ph) return `${el.tagName.toLowerCase()}[placeholder="${ph}"]`;
    const al = el.getAttribute('aria-label');
    if (al) return `[aria-label="${al}"]`;
    // aakhri raasta: parent chain
    const parts = [];
    let n = el;
    for (let i = 0; n && n.nodeType === 1 && i < 4; i++, n = n.parentElement) {
      let p = n.tagName.toLowerCase();
      if (n.parentElement) {
        const sibs = [...n.parentElement.children].filter(c => c.tagName === n.tagName);
        if (sibs.length > 1) p += `:nth-of-type(${sibs.indexOf(n) + 1})`;
      }
      parts.unshift(p);
    }
    return parts.join(' > ');
  };

  const xPath = (el) => {
    if (el.id && /^[A-Za-z][\w-]*$/.test(el.id)) return `//*[@id="${el.id}"]`;
    const fcn = el.getAttribute('formcontrolname');
    if (fcn) return `//${el.tagName.toLowerCase()}[@formcontrolname="${fcn}"]`;
    const nm = el.getAttribute('name');
    if (nm) return `//${el.tagName.toLowerCase()}[@name="${nm}"]`;
    const parts = [];
    let n = el;
    while (n && n.nodeType === 1 && n.tagName !== 'BODY') {
      const sibs = [...(n.parentElement ? n.parentElement.children : [])]
        .filter(c => c.tagName === n.tagName);
      const idx = sibs.length > 1 ? `[${sibs.indexOf(n) + 1}]` : '';
      parts.unshift(n.tagName.toLowerCase() + idx);
      n = n.parentElement;
    }
    return '/html/body/' + parts.join('/');
  };

  // Field ke paas ka label -- yahi tester ki bhasha hoti hai
  const labelOf = (el) => {
    if (el.id) {
      const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (l) return norm(l.innerText);
    }
    const aria = el.getAttribute('aria-label');
    if (aria) return norm(aria);
    let box = el.parentElement;
    for (let i = 0; box && i < 4; i++, box = box.parentElement) {
      const cands = [...box.querySelectorAll('label, span, td, th, div, p')]
        .filter(x => x.children.length === 0 && !x.contains(el));
      const hit = cands.find(x => {
        const t = norm(x.innerText);
        return t.length > 0 && t.length < 40 && !/^[*:\s]*$/.test(t);
      });
      if (hit) return norm(hit.innerText);
    }
    return '';
  };

  const seen = new Set();
  const out = [];
  const q = 'input, select, textarea, button, a[role="button"], '
          + '[role="button"], a.btn, button.btn';

  document.querySelectorAll(q).forEach(el => {
    const r = el.getBoundingClientRect();
    const visible = r.width > 0 && r.height > 0;
    const inView = visible && r.top < innerHeight && r.bottom > 0;
    if (!visible) return;
    if ((el.getAttribute('type') || '') === 'hidden') return;

    const css = cssPath(el);
    if (seen.has(css)) return;
    seen.add(css);

    const label = labelOf(el);
    const bag = [el.id, el.className, el.getAttribute('title') || '',
                 el.getAttribute('aria-label') || '', norm(el.innerText)]
                .join(' ');

    // Ek element tak pahunchne ke KAI raaste rakhte hain.
    // App badalne par aksar ek raasta toot ta hai, baaki chalte rehte hain --
    // aur test bina kisi ke chhue chalta rehta hai.
    const data = {};
    for (const a of el.attributes) {
      if (a.name.startsWith('data-') && a.value && a.value.length < 40)
        data[a.name] = a.value;
    }
    const fallbacks = [];
    const push = (kind, sel) => { if (sel && !fallbacks.some(f => f.sel === sel))
                                    fallbacks.push({kind, sel}); };
    if (el.id && /^[A-Za-z][\w-]*$/.test(el.id))
      push('id', `${el.tagName.toLowerCase()}#${el.id}`);
    for (const [k, v] of Object.entries(data))
      push('data', `[${k}="${v}"]`);
    const fcn2 = el.getAttribute('formcontrolname');
    if (fcn2) push('formcontrolname',
                   `${el.tagName.toLowerCase()}[formcontrolname="${fcn2}"]`);
    const nm2 = el.getAttribute('name');
    if (nm2) push('name', `${el.tagName.toLowerCase()}[name="${nm2}"]`);
    const al2 = el.getAttribute('aria-label');
    if (al2) push('aria', `[aria-label="${al2}"]`);
    const ph2 = el.getAttribute('placeholder');
    if (ph2) push('placeholder',
                  `${el.tagName.toLowerCase()}[placeholder="${ph2}"]`);
    const tx2 = norm(el.innerText);
    if (tx2 && tx2.length < 30 && !/["\\]/.test(tx2))
      push('text', `${el.tagName.toLowerCase()}:has-text("${tx2}")`);
    if (label && !/["\\]/.test(label)) push('nearlabel', `nearlabel=${label}`);
    push('xpath', 'xpath=' + xPath(el));

    out.push({
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      id: el.id || '',
      name: el.getAttribute('name') || '',
      fcn: el.getAttribute('formcontrolname') || '',
      placeholder: el.getAttribute('placeholder') || '',
      aria: el.getAttribute('aria-label') || '',
      data: data,
      text: norm(el.innerText || el.value || '').slice(0, 40),
      label: label,
      css: css,
      xpath: xPath(el),
      fallbacks: fallbacks,
      in_view: inView,
      danger: /(del(ete)?|trash|remove|discard|destroy|erase)/i.test(bag),
      kind: (el.tagName === 'SELECT') ? 'select'
          : (el.tagName === 'BUTTON' || el.tagName === 'A'
             || ['button','submit'].includes((el.getAttribute('type')||'').toLowerCase()))
            ? 'click' : 'type',
    });
  });
  return out;
}
"""


# ---------------------------------------------------------------- store

def _blank() -> dict:
    return {"version": 1, "screens": {}}


def load() -> dict:
    if not FILE.exists() and _OLD_FILE.exists():
        try:                    # purane naam se uthaa lo
            FILE.write_text(_OLD_FILE.read_text(encoding="utf-8"),
                            encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    if not FILE.exists():
        return _blank()
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
        return d if "screens" in d else _blank()
    except Exception:  # noqa: BLE001
        return _blank()


def save(data: dict):
    with _lock:
        FILE.parent.mkdir(parents=True, exist_ok=True)
        FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False),
                        encoding="utf-8")


def _key(el: dict) -> str:
    """Element ki apni pehchan -- do baar scan me wahi element wahi key de."""
    return el.get("id") or el.get("fcn") or el.get("name") \
        or el.get("placeholder") or el.get("css")


# ---------------------------------------------------------------- capture

def capture(page, screen: str, verbose: bool = False,
            wait: bool = True) -> dict:
    """
    Screen ke saare element scan karke catalogue me jodo.

    Scan se PEHLE page ke taiyaar hone ka intezaar hota hai. MargBooks Angular
    hai aur dheere load hota hai -- pehle main URL badalte hi scan kar leta
    tha, aur aadhe field catalogue me jate hi nahi the.

    Purani entry mitate nahi -- sirf update karte hain. Ek run me koi field
    na dikhe (popup band tha, permission nahi thi) to iska matlab ye nahi ki
    wo field hai hi nahi.
    """
    if wait:
        from framework.page_ready import wait_ready, wait_for_field_count
        st = wait_ready(page, timeout_ms=20000)
        if not st["ready"]:
            # Poori tarah shaant nahi hua -- phir bhi thode field aa gaye ho
            # to scan kar lete hain, par report me likh dete hain.
            wait_for_field_count(page, minimum=2, timeout_ms=5000)

    try:
        found = page.evaluate(SCAN_JS) or []
    except Exception:  # noqa: BLE001
        return {"screen": screen, "found": 0, "new": 0}

    data = load()
    bucket = data["screens"].setdefault(screen, {})
    now = int(time.time())
    new = 0

    for el in found:
        k = _key(el)
        if not k:
            continue
        old = bucket.get(k)
        if old:
            # Naye raaste JOD do, purane mitao mat.
            #
            # App kabhi kisi element se id hata deta hai. Us din uska naya
            # scan sirf xpath dega. Purana id-wala raasta mita dene se aage
            # ke liye gyaan kam ho jayega -- isliye dono rakhte hain.
            merged = list(old.get("fallbacks") or [])
            seen_sel = {f["sel"] for f in merged}
            for f in (el.get("fallbacks") or []):
                if f["sel"] not in seen_sel:
                    merged.append(f)
                    seen_sel.add(f["sel"])
            old.update({
                "css": el["css"], "xpath": el["xpath"],
                "label": el["label"] or old.get("label", ""),
                "data": el.get("data") or old.get("data") or {},
                "fallbacks": merged[:8],
                "in_view": el["in_view"], "seen": old.get("seen", 0) + 1,
                "last": now,
            })
        else:
            bucket[k] = {**el, "seen": 1, "first": now, "last": now}
            new += 1

    save(data)
    if verbose and new:
        print(f"  [catalogue] {screen}: {new} naye element seekhe "
              f"(kul {len(bucket)})")
    return {"screen": screen, "found": len(found), "new": new,
            "total": len(bucket)}


# ---------------------------------------------------------------- resolve

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    """'M.R.P' -> ['m','r','p'] ; 'txtItemName' -> ['txt','item','name']"""
    t = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(text or ""))
    return _WORD.findall(t.lower())


def _score(el: dict, want: list[str]) -> int:
    """Ye element us phrase se kitna milta hai."""
    if not want:
        return 0
    best = 0
    for field, weight in (("label", 100), ("placeholder", 90), ("aria", 90),
                          ("text", 85), ("fcn", 70), ("id", 65), ("name", 60)):
        toks = _tokens(el.get(field, ""))
        if not toks:
            continue
        # 'txt' jaisa prefix hata do -- wo naam ka hissa nahi
        toks = [t for t in toks if t not in ("txt", "btn", "input", "field")]
        if not toks:
            continue
        if toks == want:
            best = max(best, weight)
        elif set(want).issubset(set(toks)):
            best = max(best, weight - 12)
        else:
            hit = len(set(want) & set(toks))
            if hit:
                best = max(best, int(weight * hit / max(len(want), len(toks))) - 5)
    return best


def resolve(screen: str, phrase: str, kind: str = "any",
            min_score: int = 55) -> dict | None:
    """
    Layman phrase se element dhoondho.

        resolve("item_create", "Item Name", kind="type")
        -> {"css": "input#txtItemName", "xpath": "...", "score": 100, ...}

    kind: "type" (likhne wala), "click" (button), "select", "any"
    Bharosa kam ho to None -- andaza lagana chupchaap galat locator dene se
    bura hai.
    """
    bucket = load()["screens"].get(screen) or {}
    want = _tokens(phrase)
    if not want:
        return None

    scored = []
    for k, el in bucket.items():
        if el.get("danger"):
            continue                      # delete wale kabhi nahi
        if kind != "any":
            if kind == "type" and el.get("kind") not in ("type", "select"):
                continue
            if kind == "click" and el.get("kind") != "click":
                continue
            if kind == "select" and el.get("kind") != "select":
                continue
        # likhne ke liye input, select tabhi jab aur kuch na ho
        s = _score(el, want)
        if kind == "type" and el.get("kind") == "select":
            s -= 15
        if not el.get("in_view"):
            s -= 10                       # chhupa hua element kam bharosemand
        if s > 0:
            scored.append((s, k, el))

    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    top_score, key, el = scored[0]
    if top_score < min_score:
        return None

    # do element barabar ke paas hon to bharosa kam hai
    ambiguous = len(scored) > 1 and scored[1][0] >= top_score - 5
    return {
        "key": key, "css": el["css"], "xpath": el["xpath"],
        "label": el.get("label", ""), "kind": el.get("kind"),
        "score": top_score, "ambiguous": ambiguous,
        # Sabse pakka pehle. Pehla na chale to agla -- app badalne par
        # aksar ek hi raasta tootta hai.
        "selectors": [f["sel"] for f in (el.get("fallbacks") or [])] or [el["css"]],
        "others": [s[2].get("label") or s[1] for s in scored[1:4]],
    }


def suggestions(screen: str, phrase: str, n: int = 5) -> list[str]:
    """Na mile to milte-julte naam -- error me dikhane ke liye."""
    bucket = load()["screens"].get(screen) or {}
    want = _tokens(phrase)
    out = [(( _score(el, want)), el.get("label") or el.get("id") or k)
           for k, el in bucket.items() if not el.get("danger")]
    out.sort(key=lambda x: -x[0])
    return [name for score, name in out[:n] if score > 0] or \
           [ (el.get("label") or k) for k, el in list(bucket.items())[:n] ]


# ---------------------------------------------------------------- report

def stats() -> dict:
    d = load()
    per = {s: len(v) for s, v in d["screens"].items()}
    return {"screens": len(per), "elements": sum(per.values()), "per_screen": per}


def screen_elements(screen: str) -> list[dict]:
    bucket = load()["screens"].get(screen) or {}
    rows = []
    for k, el in bucket.items():
        rows.append({
            "key": k, "label": el.get("label", ""), "kind": el.get("kind"),
            "css": el.get("css"), "xpath": el.get("xpath"),
            "id": el.get("id", ""), "placeholder": el.get("placeholder", ""),
            "danger": bool(el.get("danger")), "seen": el.get("seen", 0),
            "selectors": [f["sel"] for f in (el.get("fallbacks") or [])],
        })
    rows.sort(key=lambda r: (r["danger"], -r["seen"], r["label"]))
    return rows


def report(path) -> str | None:
    d = stats()
    if not d["elements"]:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"ELEMENT CATALOGUE -- {d['elements']} element, {d['screens']} screen",
             "(locators/catalogue.json me save hai; har run me badhta hai)", ""]
    for screen, count in sorted(d["per_screen"].items(), key=lambda x: -x[1]):
        lines.append(f"--- {screen} ({count}) ---")
        for r in screen_elements(screen)[:25]:
            mark = "  !! " if r["danger"] else "     "
            lines.append(f"{mark}{(r['label'] or r['key'])[:34]:<34} "
                         f"{r['kind']:<7} {r['css']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
