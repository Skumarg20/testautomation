"""
AI se locator theek karna -- sabse aakhri raasta.

KAB CHALTA HAI
--------------
Locator dhoondhne ka kram ye hai, aur AI SABSE AAKHIR me aata hai:

    1. locators/margbooks.yaml     -- haath se likhe, sabse pakke
    2. locators_registry.json      -- agent ne khud dekhe hue (kai raaste)
    3. autolearn (niyam)           -- page pe shabd milाकर dhoondhna
    4. AI (yahan)                  -- baaki sab fail ho jaye tab

Ye kram jaan-boojh kar hai. Upar wale teen har baar bilkul EK JAISA natija
dete hain aur muft hain. AI na to dono deta hai, isliye wo aakhri hai --
pehla nahi.

KYA BHEJA JATA HAI
------------------
Poora HTML nahi -- sirf CHHANT KAR nikaale gaye elements ki chhoti list:
tag, id, label, placeholder. Koi value nahi jaati, isliye password, GSTIN
ya kisi party ka data kabhi nahi jata.

JO SEEKHA WO WAPAS REGISTRY ME
------------------------------
AI ka bataya selector pehle SACH ME jaancha jata hai (element maujood hai?
sahi tarah ka hai? khatarnak to nahi?). Tabhi registry me likha jata hai.
Agli baar wahi locator bina AI ke mil jayega -- yaani AI ek hi baar lagta
hai, har baar nahi.
"""
from __future__ import annotations

import json

from framework import catalogue, safety

# Page se chhant kar elements nikaalne wala JS.
# Sirf wahi jo DIKH rahe hain aur jinse kaam ho sakta hai.
SLIM_DOM_JS = r"""
(want) => {
  const norm = t => (t || '').replace(/\s+/g, ' ').trim();

  const labelOf = (el) => {
    if (el.id) {
      const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (l && norm(l.innerText)) return norm(l.innerText);
    }
    let box = el.parentElement;
    for (let i = 0; box && i < 4; i++, box = box.parentElement) {
      const c = [...box.querySelectorAll('label,span,td,div,p')]
        .find(x => x.children.length === 0 && !x.contains(el)
                   && norm(x.innerText).length > 1
                   && norm(x.innerText).length < 40);
      if (c) return norm(c.innerText);
    }
    return '';
  };

  const q = want === 'click'
    ? 'button, a, [role=button], input[type=button], input[type=submit]'
    : want === 'type'
    ? 'input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea'
    : 'input:not([type=hidden]), select, textarea, button, a, [role=button]';

  // Delete/remove wale element AI ko DIKHTE HI NAHI.
  // Jo cheez list me hai hi nahi, use AI chun hi nahi sakta -- ye rokne se
  // behtar hai ki baad me pakadna pade.
  const DANGER = /(del(ete)?|trash|remove|discard|destroy|erase)/i;

  const out = [];
  document.querySelectorAll(q).forEach((el, i) => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    if (r.top > innerHeight * 3 || r.bottom < 0) return;
    const bag = [el.id, el.className, el.getAttribute('title') || '',
                 el.getAttribute('aria-label') || '',
                 (el.innerText || '')].join(' ');
    if (DANGER.test(bag)) return;
    // Sirf pehchan bhejte hain -- VALUE kabhi nahi.
    out.push({
      i,
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      id: el.id || '',
      fcn: el.getAttribute('formcontrolname') || '',
      name: el.getAttribute('name') || '',
      ph: el.getAttribute('placeholder') || '',
      aria: el.getAttribute('aria-label') || '',
      text: norm(el.innerText).slice(0, 30),
      label: labelOf(el).slice(0, 40),
    });
  });
  return out.slice(0, 90);
}
"""

HEAL_SYSTEM = """You match a QA test's field name to the right element on a page.

You get: the name the tester used, and a list of elements now on screen.
Pick the ONE element that a person would click or type into for that name.

Rules:
- Prefer the element whose visible label matches. Ids are a weak hint --
  MargBooks ids are cryptic and reused across unrelated panels.
- Never pick anything about delete, remove or trash.
- If nothing clearly matches, return index -1. A wrong guess is far worse
  than saying no: it silently makes the test check the wrong thing.

Return JSON only: {"index": <number>, "why": "<max 12 words>"}"""


class HealFailed(RuntimeError):
    pass


def heal(page, key: str, want: str = "any", verbose: bool = True) -> dict | None:
    """
    AI se poochho ki '<key>' kaunsa element hai.

    None -- agar AI key nahi hai, ya AI ne bhi mana kar diya, ya uska
    bataya element jaanch me fail ho gaya.
    """
    from framework import ai

    if not ai.available()["active"]:
        return None

    try:
        elements = page.evaluate(SLIM_DOM_JS, want)
    except Exception:  # noqa: BLE001
        return None
    if not elements:
        return None

    phrase = key.split(".")[-1].replace("_", " ")
    try:
        out = ai.ask_json(
            HEAL_SYSTEM,
            f'Field the tester asked for: "{phrase}"\n\n'
            f"Elements on screen:\n{json.dumps(elements, ensure_ascii=False)}",
            max_tokens=2048)
    except ai.AIError as e:
        if verbose:
            print(f"  [heal] AI se madad nahi mili: {str(e)[:90]}")
        return None

    idx = out.get("index", -1)
    if not isinstance(idx, int) or idx < 0:
        if verbose:
            print(f"  [heal] AI ne bhi mana kiya '{phrase}' ke liye "
                  f"({out.get('why', '')})")
        return None

    hit = next((e for e in elements if e["i"] == idx), None)
    if not hit:
        return None

    selector = _selector_for(hit)
    if not selector:
        return None

    # AI ki baat par bharosa nahi -- KHUD jaanch karo
    ok, why = _verify(page, selector, want)
    if not ok:
        if verbose:
            print(f"  [heal] AI ne '{selector}' bataya, par {why} -- chhod diya")
        return None

    _remember(page, key, hit, selector)
    if verbose:
        print(f"  [heal] AI SE MILA  {key} -> {selector}  "
              f"({out.get('why', '')})")
    return {"key": key, "selector": selector, "why": out.get("why", ""),
            "label": hit.get("label", ""), "source": "ai"}


def _selector_for(el: dict) -> str | None:
    """Element ki pehchan se sabse pakka selector."""
    tag = el.get("tag", "")
    if el.get("id") and el["id"].replace("-", "").replace("_", "").isalnum():
        return f"{tag}#{el['id']}"
    for attr, name in (("fcn", "formcontrolname"), ("name", "name"),
                       ("ph", "placeholder")):
        if el.get(attr) and '"' not in el[attr]:
            return f'{tag}[{name}="{el[attr]}"]'
    if el.get("aria") and '"' not in el["aria"]:
        return f'[aria-label="{el["aria"]}"]'
    if el.get("text") and len(el["text"]) < 30 and '"' not in el["text"]:
        return f'{tag}:has-text("{el["text"]}")'
    return None


def _verify(page, selector: str, want: str) -> tuple[bool, str]:
    """
    AI ka bataya element sach me theek hai?

    Teen jaanch: maujood hai, sahi tarah ka hai, aur khatarnak nahi hai.
    Bina jaanche registry me likhna wahi galti hogi jo autolearn ke saath
    ek baar ho chuki hai -- Settings panel ka dropdown Party field samajh
    kar save ho gaya tha.
    """
    try:
        loc = page.locator(selector).first
        if loc.count() == 0:
            return False, "wo element mila hi nahi"
        tag = loc.evaluate("e => e.tagName.toLowerCase()")
    except Exception as e:  # noqa: BLE001
        return False, f"jaanch nahi ho payi ({str(e)[:40]})"

    if want == "type" and tag not in ("input", "textarea"):
        return False, f"usme likha nahi ja sakta (<{tag}>)"
    if want == "click" and tag not in ("button", "a", "input"):
        return False, f"wo click karne wala nahi hai (<{tag}>)"

    # Apni jaanch -- safety.assert_safe par nirbhar nahi.
    #
    # assert_safe ALLOW_DESTRUCTIVE=true hone par chup ho jata hai, aur wo
    # theek hai: jaan-boojh kar likhe delete test ko rokna nahi chahiye.
    # Par AI ka delete button CHUN lena alag baat hai -- wo locator ki galti
    # hai, ijazat ki nahi. Isliye ye jaanch hamesha chalti hai.
    try:
        bag = loc.evaluate("""e => [e.id, e.className, e.getAttribute('title')||'',
                                    e.getAttribute('aria-label')||'',
                                    (e.innerText||'')].join(' ')""")
    except Exception:  # noqa: BLE001
        bag = ""
    if safety.DANGER_ATTR.search(bag or "") or \
            (bag or "").strip().lower() in safety.DANGER_TEXT:
        return False, "wo delete/remove wala element hai"

    try:
        safety.assert_safe(loc, f"heal:{selector}")
    except safety.UnsafeClick:
        return False, "wo delete/remove wala element hai"
    except Exception:  # noqa: BLE001
        pass
    return True, ""


def _remember(page, key: str, el: dict, selector: str):
    """Registry me likh do -- agli baar AI ki zaroorat na pade."""
    from framework.base_page import BasePage
    try:
        screen = BasePage(page).current_screen()
    except Exception:  # noqa: BLE001
        screen = "unknown"

    data = catalogue.load()
    bucket = data["screens"].setdefault(screen, {})
    k = el.get("id") or el.get("fcn") or el.get("name") or selector
    row = bucket.get(k, {})
    fallbacks = list(row.get("fallbacks") or [])
    if not any(f["sel"] == selector for f in fallbacks):
        fallbacks.insert(0, {"kind": "ai", "sel": selector})
    row.update({
        "tag": el.get("tag", ""), "id": el.get("id", ""),
        "fcn": el.get("fcn", ""), "name": el.get("name", ""),
        "placeholder": el.get("ph", ""), "aria": el.get("aria", ""),
        "text": el.get("text", ""), "label": el.get("label", ""),
        "css": selector, "fallbacks": fallbacks[:8],
        "kind": row.get("kind") or ("click" if el.get("tag") in ("button", "a")
                                    else "type"),
        "in_view": True, "danger": False,
        "seen": row.get("seen", 0) + 1, "healed_for": key,
    })
    bucket[k] = row
    catalogue.save(data)


HEALED: list[dict] = []


def remember(info: dict):
    HEALED.append(info)


def report(path) -> str | None:
    if not HEALED:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["AI NE YE LOCATOR THEEK KIYE",
             "(registry me save ho chuke hain -- ek baar dekh lo)", ""]
    for h in HEALED:
        lines.append(f"  {h['key']:<26} -> {h['selector']}")
        lines.append(f"      label: {h.get('label', '')!r}  |  {h.get('why', '')}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
