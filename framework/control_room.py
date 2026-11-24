"""
Control Room ki settings padhna aur yaad rakhna.

KYUN YE SABSE ZAROORI HISSA HAI
-------------------------------
MargBooks ka poora vyavhaar Control Room pe tika hai. Ek hi Sale Bill do
company me bilkul alag dikhta hai, sirf isliye ki settings alag hain:

    Mode of Payment ON      -> save karte waqt ek aur window khulti hai
    Ask Bill Discount OFF   -> discount ka field hota hi nahi
    Stock Negative = No     -> stock se zyada bechne par app rok deta hai
    Calculation = Inclusive -> GST ka hisaab hi alag hoga

Iska matlab: settings jaane bina test likhna andhere me teer chalana hai.
Test fail hoga aur pata nahi chalega ki bug hai ya sirf setting band thi.

Isliye agent ab Control Room khud khol kar SAARI settings padh leta hai aur
config/control_room.json me rakh leta hai. Uske baad:
  - test declare kar sakta hai "mujhe mode_of_payment chahiye"
  - setting OFF ho to test FAIL nahi, SKIP hota hai (saaf wajah ke saath)
  - report me likha rehta hai ki us run me kaunsi settings thin
"""
from __future__ import annotations

import json
import os
import re
import time

from config.settings import ROOT, settings
from framework import safety
from framework.base_page import BasePage
from framework.page_ready import wait_ready

FILE = ROOT / "config" / "control_room.json"


class FeatureOff(Exception):
    """Feature Control Room me band hai -- ye BUG NAHI hai."""


class ControlRoomNotOpen(RuntimeError):
    pass


# Jin settings ka asar humare tests par padta hai.
#
# Ye list CODE ME NAHI hai -- config/prerequisites.json me hai.
#
# Pehle ye ek Python dict tha. Uska matlab tha: naya field jodne ke liye
# code chhedna padega, aur agla update us badlav ko mita dega. Tester khud
# kuch nahi jod paata tha. Ab wo ek JSON file hai jise koi bhi likh sakta hai.
KNOWN_FILE = ROOT / "config" / "prerequisites.json"


def _load_known() -> dict:
    """prerequisites.json -> {name: {labels, aliases, affects, ...}}"""
    try:
        raw = json.loads(KNOWN_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for row in raw.get("configurations", []):
        name = row.get("name")
        if not name:
            continue
        out[name] = {
            "labels": row.get("labels") or [name.replace("_", " ").title()],
            "aliases": [a.lower() for a in (row.get("aliases") or [])],
            "affects": row.get("affects", ""),
            "kind": row.get("kind", "toggle"),
            "enable": row.get("enable", "Yes"),
        }
    return out


KNOWN: dict[str, dict] = _load_known()


def reload_known():
    """JSON badalne ke baad -- server restart kiye bina."""
    global KNOWN
    KNOWN = _load_known()
    return len(KNOWN)


def find_by_phrase(phrase: str) -> str | None:
    """
    Tester ki bhasha se setting ka naam.

        "discount one" -> ask_item_discount
        "disc 1"       -> ask_item_discount
        "batch"        -> batch_required

    Yahi wo cheez hai jo "Set Discount 1 to 10" jaise prompt ko sahi
    setting se jodti hai -- bina har field ke liye alag code likhe.
    """
    want = " ".join(re.findall(r"[a-z0-9]+", str(phrase or "").lower()))
    if not want:
        return None
    for name, info in KNOWN.items():
        if want == name.replace("_", " "):
            return name
        for a in info["aliases"]:
            if want == a or (a in want and len(a) > 3):
                return name
        for lab in info["labels"]:
            low = " ".join(re.findall(r"[a-z0-9]+", lab.lower()))
            if want == low or (want in low and len(want) > 4):
                return name
    return None


SCAN_JS = r"""
() => {
  const norm = t => (t || '').replace(/\s+/g, ' ').trim();

  const valueOf = (el) => {
    const t = (el.getAttribute('type') || '').toLowerCase();
    if (el.tagName === 'SELECT') {
      const o = el.options[el.selectedIndex];
      return o ? norm(o.text) : '';
    }
    if (t === 'checkbox' || t === 'radio') return el.checked ? 'Yes' : 'No';
    return el.value || '';
  };

  const labelFor = (el) => {
    if (el.id) {
      const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (l && norm(l.innerText)) return norm(l.innerText);
    }
    let box = el.parentElement;
    for (let i = 0; box && i < 5; i++, box = box.parentElement) {
      const cands = [...box.querySelectorAll('label, span, div, td, p')]
        .filter(x => x.children.length === 0 && !x.contains(el));
      const hit = cands.find(x => {
        const s = norm(x.innerText);
        return s.length > 2 && s.length < 60 && !/^(yes|no|on|off)$/i.test(s);
      });
      if (hit) return norm(hit.innerText);
    }
    return '';
  };

  const cssOf = (el) => {
    if (el.id && /^[A-Za-z][\w-]*$/.test(el.id))
      return `${el.tagName.toLowerCase()}#${el.id}`;
    const fcn = el.getAttribute('formcontrolname');
    if (fcn) return `${el.tagName.toLowerCase()}[formcontrolname="${fcn}"]`;
    const nm = el.getAttribute('name');
    if (nm) return `${el.tagName.toLowerCase()}[name="${nm}"]`;
    return '';
  };

  const out = [];
  const seen = new Set();
  document.querySelectorAll(
    'select, input[type=checkbox], input[type=radio], input[type=text], '
    + '[role=switch], .toggle, [class*="switch"]'
  ).forEach(el => {
    const r = el.getBoundingClientRect();
    const hidden = r.width === 0 && r.height === 0;
    const label = labelFor(el);
    if (!label) return;
    const css = cssOf(el);
    const key = css || label;
    if (seen.has(key)) return;
    seen.add(key);
    const options = el.tagName === 'SELECT'
      ? [...el.options].map(o => norm(o.text)).slice(0, 12) : [];
    out.push({
      label, css, id: el.id || '',
      kind: el.tagName === 'SELECT' ? 'choice'
          : (el.getAttribute('type') || '').toLowerCase() === 'checkbox'
            ? 'toggle' : 'text',
      value: valueOf(el), options, hidden,
    });
  });
  return {url: location.href, count: out.length, settings: out};
}
"""


def load() -> dict:
    if not FILE.exists():
        return {"read_at": None, "settings": {}, "raw": []}
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"read_at": None, "settings": {}, "raw": []}


def save(data: dict):
    import os
    if os.environ.get("MB_NO_CAPTURE"):      # parallel sessions (tools/live_session): no shared-file writes
        return
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False),
                    encoding="utf-8")


def is_on(value) -> bool | None:
    """'Yes'/'No'/"Don't Ask" waghairah ko ek jaisa banao."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    v = str(value).strip().lower()
    if v in ("yes", "true", "1", "on", "required", "always", "ask"):
        return True
    if v in ("no", "false", "0", "off", "don't ask", "dont ask", "never"):
        return False
    return None


def _norm(t: str) -> str:
    return "".join(ch for ch in str(t).lower() if ch.isalnum())


def _match_known(rows: list[dict]) -> dict:
    """
    Screen ke labels ko humare known keys se jodo.

    'startswith' se sirf 4 settings pehchani gayin, kyunki asli labels lambe
    hote hain: "Mode of Payment required in Sale". Ab 'contains' se dekhte
    hain -- pehle poora label, phir uska hissa.
    """
    out = {}
    used = set()
    for key, info in KNOWN.items():
        best = None
        for want in info["labels"]:
            w = _norm(want)
            # pehle bilkul barabar, phir jisme ye shabd aate hon
            for test in (lambda r: _norm(r["label"]) == w,
                         lambda r: w in _norm(r["label"]),
                         lambda r: _norm(r["label"]) in w and len(_norm(r["label"])) > 8):
                hit = next((r for r in rows
                            if id(r) not in used and test(r)), None)
                if hit:
                    best = hit
                    break
            if best:
                break
        if not best:
            continue
        used.add(id(best))
        kind = best.get("kind", "toggle")
        out[key] = {
            "label": best["label"], "value": best["value"],
            # choice wali setting par ON/OFF poochna hi galat sawaal hai --
            # "Inclusive" na ON hai na OFF. Uske liye 'on' None rehta hai
            # aur report me uski value hi dikhti hai.
            "on": is_on(best["value"]) if kind != "choice" else None,
            "kind": kind,
            "css": best.get("css", ""),
            "options": best.get("options", []),
            "affects": info["affects"],
        }
    return out


# Settings page par kai card hote hain, aur HAR EK par "Configure" likha
# hota hai -- User Privilege, Control Room, Company Details, aur bhi.
# Pehla "Configure" daba dene se User Privilege khul jata tha.
#
# Isliye pehle "Control Room" wala CARD dhoondhte hain, phir usi card ke
# andar ka button. Wahi tareeka jo "Bill" ke saamne wale "+" ke liye lagaya
# tha -- akela button dhoondhna hamesha galat nikalta hai.
FIND_CARD_JS = r"""
(title) => {
  const norm = t => (t || '').replace(/\s+/g, ' ').trim();
  const want = norm(title).toLowerCase();

  // 1. wo element jiska apna text "Control Room" ho
  const leaves = [...document.querySelectorAll('h1,h2,h3,h4,h5,span,div,p,label,a,td')]
    .filter(e => e.children.length === 0 && e.offsetHeight > 0);
  const hit = leaves.find(e => norm(e.innerText).toLowerCase() === want)
           || leaves.find(e => norm(e.innerText).toLowerCase().startsWith(want));
  if (!hit) return {found: false, reason: `'${title}' page pe nahi mila`};

  // 2. uske card/row me upar chadhte hue button dhoondho
  let box = hit.parentElement;
  for (let i = 0; box && i < 5; i++, box = box.parentElement) {
    const btns = [...box.querySelectorAll('button, a, .btn, [role=button]')]
      .filter(b => b.offsetHeight > 0);
    const cfg = btns.find(b => /configure|settings|open|manage/i.test(norm(b.innerText)))
             || (btns.length === 1 ? btns[0] : null);
    if (cfg) {
      // Doosre card ka button na uth jaye -- card me title bhi hona chahiye
      if (!norm(box.innerText).toLowerCase().includes(want)) continue;
      cfg.setAttribute('data-mb-cfg', '1');
      return {found: true, text: norm(cfg.innerText),
              card: norm(box.innerText).slice(0, 90)};
    }
  }
  return {found: false, reason: `'${title}' ke paas koi Configure button nahi mila`};
}
"""


def click_card_button(bp: BasePage, title: str, verbose: bool = False) -> bool:
    """'Control Room' wale card ka Configure dabao -- kisi aur card ka nahi."""
    page = bp.page
    page.evaluate("() => document.querySelectorAll('[data-mb-cfg]')"
                  ".forEach(e => e.removeAttribute('data-mb-cfg'))")
    info = page.evaluate(FIND_CARD_JS, title)
    if not info.get("found"):
        if verbose:
            print(f"  [control room] {info.get('reason')}")
        return False
    if verbose:
        print(f"  [control room] '{title}' card mila -> '{info['text']}' daba rahe hain")
    try:
        safety.guarded_click(page.locator("[data-mb-cfg]").first,
                             f"card:{title}", timeout=6000)
        wait_ready(page, timeout_ms=20000)
        return True
    except Exception as e:  # noqa: BLE001
        if verbose:
            print(f"  [control room] click fail: {str(e)[:90]}")
        return False


def open_control_room(bp: BasePage, verbose: bool = False) -> bool:
    """
    Settings icon -> Control Room wala card -> uska Configure

    Har kadam par jaanch hoti hai. Pehle ye seedha "pehla Configure" daba
    deta tha aur User Privilege khul jata tha.
    """
    page = bp.page
    # Already open with its rows (an earlier ensure/read left it open)? Use it: the Settings icon toggles the
    # panel, so clicking it again closed it and the next scan read no rows (TC_CSAL_003: "Close labels: []").
    try:
        raw = page.evaluate(SCAN_JS)
        if len([r for r in raw.get("settings", []) if not r.get("hidden")]) > 50:
            return True
    except Exception:  # noqa: BLE001
        pass
    safety.dismiss_modal(page)

    # 1. Settings
    try:
        bp.click("nav.settings")
    except Exception:  # noqa: BLE001
        try:
            safety.guarded_click(page.locator("a#aControlRoomSetting").first,
                                 "nav.settings", timeout=4000)
        except Exception:  # noqa: BLE001
            # Seen in Studio runs (TC_GARM_092, TC_SALE_044): the icon is on screen but Playwright cannot find
            # it any more after a long run (its view of the page went stale). Loading the dashboard again
            # gives a fresh page; then the icon is found at once.
            try:
                try:                                    # what the page itself sees (for the run log)
                    seen = page.evaluate("() => { const e = document.getElementById('aControlRoomSetting'); "
                                         "return e ? (e.offsetParent ? 'visible' : 'hidden') : 'missing'; }")
                    print(f"  [control_room] Settings icon not found by Playwright; in the page it is {seen}. "
                          f"Reloading the dashboard.")
                except Exception:  # noqa: BLE001
                    pass
                bp.goto(f"{settings.BASE_URL}/dashboard", check_auth=False)
                page.wait_for_timeout(3000)
                safety.guarded_click(page.locator("a#aControlRoomSetting").first, "nav.settings", timeout=15000)
            except Exception as e:  # noqa: BLE001
                raise ControlRoomNotOpen(f"Settings ka icon nahi mila: {e}") from e
    wait_ready(page, timeout_ms=15000, verbose=verbose)

    # 2. Control Room wale card ka Configure
    if not click_card_button(bp, "Control Room", verbose=verbose):
        # kabhi seedha panel khul jata hai -- tab card ki zaroorat nahi
        if not _looks_like_control_room(page):
            cards = _list_cards(page)
            raise ControlRoomNotOpen(
                "Settings me 'Control Room' ka card nahi mila.\n"
                f"  Ye card dikhe: {cards}\n"
                f"  URL: {page.url}")

    # 3. pakka karo ki SAHI panel khula hai
    if not _looks_like_control_room(page):
        raise ControlRoomNotOpen(
            "Configure to daba, par Control Room nahi khula.\n"
            f"  Screen par ye dikh raha hai: {_heading(page)!r}\n"
            f"  URL: {page.url}")

    if verbose:
        print(f"  [control room] khul gaya -- {_heading(page)!r}")
    return True


def _heading(page) -> str:
    try:
        return page.evaluate(
            "() => { const h = document.querySelector('h1,h2,h3,.mhead,.modal-title');"
            "  return h ? (h.innerText||'').trim().slice(0,60) : ''; }") or ""
    except Exception:  # noqa: BLE001
        return ""


def _list_cards(page) -> list[str]:
    """Settings page par kaunse card hain -- error me dikhane ke liye."""
    try:
        return page.evaluate(r"""
          () => [...document.querySelectorAll('h1,h2,h3,h4,h5,.card-title,strong')]
                 .map(e => (e.innerText||'').replace(/\s+/g,' ').trim())
                 .filter(t => t.length > 2 && t.length < 45).slice(0, 12)
        """) or []
    except Exception:  # noqa: BLE001
        return []


def _looks_like_control_room(page) -> bool:
    """
    Sahi panel khula hai ya koi aur?

    User Privilege bhi "Configure" se khulta hai aur dekhne me settings jaisa
    hi lagta hai. Isliye Control Room ke apne shabd dhoondhte hain.
    """
    try:
        body = (page.inner_text("body") or "").lower()
    except Exception:  # noqa: BLE001
        return False
    # User Privilege ke apne shabd -- ye mile to GALAT panel hai
    if any(w in body for w in ("user privilege", "user rights", "assign user")):
        if "billing requirement" not in body and "control room" not in body:
            return False
    return any(w in body for w in (
        "control room", "billing requirement", "discount & sale logic",
        "stock & product handling", "transaction preference"))


def read(bp: BasePage, verbose: bool = False) -> dict:
    """Jo panel abhi khula hai usse saari settings padho aur file me likho."""
    wait_ready(bp.page, timeout_ms=20000, verbose=verbose)
    try:
        raw = bp.page.evaluate(SCAN_JS)
    except Exception as e:  # noqa: BLE001
        raise ControlRoomNotOpen(f"Settings padhi nahi ja sakin: {e}") from e

    rows = [r for r in raw.get("settings", []) if not r.get("hidden")]
    known = _match_known(rows)
    data = {"read_at": time.strftime("%Y-%m-%d %H:%M"),
            "url": raw.get("url", ""), "total": len(rows),
            "settings": known, "raw": rows}
    save(data)
    if verbose:
        print(f"  [control room] {len(rows)} settings padhin, "
              f"{len(known)} pehchani gayin")
    return data


def read_from_open_form(bp: BasePage) -> dict:
    """Sale Bill ka "Set Transaction Preferences" popup khula ho to usse padho."""
    try:
        raw = bp.page.evaluate(SCAN_JS)
    except Exception:  # noqa: BLE001
        return {}
    return _match_known([r for r in raw.get("settings", []) if not r.get("hidden")])


def capture(bp: BasePage, verbose: bool = False) -> dict:
    """Control Room kholo, padho, band karo."""
    if not open_control_room(bp, verbose=verbose):
        raise ControlRoomNotOpen(
            "Control Room khul nahi paya. Settings icon -> Control Room -> "
            "Configure ka rasta badal gaya ho sakta hai.")
    data = read(bp, verbose=verbose)
    safety.force_close_modal(bp.page)
    return data


def get(feature: str) -> dict | None:
    return load().get("settings", {}).get(feature)


def require(bp: BasePage | None, feature: str, snapshot: dict | None = None):
    """
    Test ke shuru me: control_room.require(bp, "mode_of_payment")

    OFF ho to FeatureOff -- jise runner SKIP maanta hai, FAIL nahi.
    App theek hai, bas setting band hai.
    """
    info = KNOWN.get(feature)
    if not info:
        raise KeyError(f"'{feature}' known settings me nahi. Ye hain: {sorted(KNOWN)}")

    row = (snapshot or {}).get(feature) or get(feature)
    if row is None:
        raise FeatureOff(
            f"'{feature}' ki setting abhi padhi hi nahi gayi.\n"
            f"  Ek baar control-room.bat chala do -- uske baad ye test apne "
            f"aap sahi faisla lega.")
    if row.get("kind") == "choice":
        return          # choice setting band nahi hoti, bas alag hoti hai
    if row.get("on") is False:
        raise FeatureOff(
            f"'{feature}' Control Room me OFF hai -- {info['affects']}.\n"
            f"  Screen par likha hai: {row.get('label')} = {row.get('value')}\n"
            f"  Ye bug NAHI hai. Chalane ke liye Settings > Control Room me "
            f"isse ON karo.")


# ---------------------------------------------------------------- badalna

class SettingLocked(RuntimeError):
    """Setting badalni thi par ijazat nahi hai."""


# Setting badalne ki ijazat -- ALLOW_DESTRUCTIVE se ALAG.
#
# ASLI KHATRA: crawler ko Control Room ki setting badalni hoti hai (--enable),
# aur uske liye ALLOW_DESTRUCTIVE=true chahiye tha. Wahi flag click-guard aur
# delete-request block ko bhi band kar deta hai -- yaani poore crawl me (list
# pages par trash icons ke saath) koi pehra nahi rehta tha.
#
# Ab crawler guard ON rakhta hai, aur sirf ye ek flag kholta hai: "Control Room
# ki setting badalna theek hai". Isse kuch aur nahi khulta.
SETTINGS_WRITE_OK = False


def allow_settings_change(on: bool = True):
    global SETTINGS_WRITE_OK
    SETTINGS_WRITE_OK = bool(on)


KIND_JS = """
(sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  return {tag: el.tagName.toLowerCase(),
          type: (el.getAttribute('type') || '').toLowerCase(),
          checked: !!el.checked,
          options: el.tagName === 'SELECT'
            ? [...el.options].map(o => (o.text || '').trim()) : [],
          now: el.tagName === 'SELECT'
            ? ((el.options[el.selectedIndex] || {}).text || '').trim()
            : (el.checked ? 'Yes' : 'No')};
}
"""


def _set_control(bp: BasePage, css: str, want: str) -> dict:
    """
    Ek setting ka control badlo -- Playwright ke apne tareeke se.

    Pehle ye JS ke andar el.click() se hota tha. Wo chalta to tha, par
    delete-guard ko POORI TARAH bypass kar deta tha: guard Playwright ke
    click par lagta hai, JS ke andar wale par nahi. Ek jagah chhed rakhna
    aur baaki sab jagah pehra lagana bemaani hai.
    """
    info = bp.page.evaluate(KIND_JS, css)
    if not info:
        return {"ok": False, "why": "element nahi mila"}

    loc = bp.page.locator(css).first
    safety.assert_safe(loc, f"controlroom:{css}")

    if info["tag"] == "select":
        if not any(o.lower() == str(want).lower() for o in info["options"]):
            return {"ok": False,
                    "why": f"'{want}' vikalp nahi hai "
                           f"({' / '.join(info['options'])})"}
        if info["now"].lower() == str(want).lower():
            return {"ok": True, "changed": False, "now": info["now"]}
        loc.select_option(label=want)
        # Some Control Room rows only mark the form dirty on a real user-like change: make sure Angular sees
        # it (seen: Net Scheme / Batch Window Index on reverted when only select_option was used).
        try:
            loc.dispatch_event("input")
            loc.dispatch_event("change")
            loc.press("Tab")
        except Exception:  # noqa: BLE001
            pass
        bp.settle()
        return {"ok": True, "changed": True, "now": want}

    if info["type"] in ("checkbox", "radio"):
        target = str(want).lower() in ("yes", "true", "on", "1")
        if info["checked"] == target:
            return {"ok": True, "changed": False,
                    "now": "Yes" if target else "No"}
        safety.audit_click(loc, f"controlroom:{css}")
        loc.set_checked(target)          # Angular ko asli event milta hai
        bp.settle()
        return {"ok": True, "changed": True, "now": "Yes" if target else "No"}

    return {"ok": False, "why": f"<{info['tag']}> badalna nahi aata"}


def ensure(bp: BasePage, feature: str, want: str = "Yes",
           verbose: bool = False) -> dict:
    """
    Setting ko chaahi hui haalat me LAO -- pehle se waisi na ho to badal do.

    YE KAB ZAROORI HAI
    ------------------
    Kuch test bina kisi setting ke chal hi nahi sakte. "Discount 1 me 10
    daalo" tab tak bemaani hai jab tak Control Room me item discount ON na
    ho -- wo field hi nahi hota.

    Ab tak hum aise test ko SKIP kar dete the. Wo imaandaar tha, par kaam
    aage nahi badhta tha. Ab pehle setting ON karte hain, phir test chalta hai.

    DO ROK
    ------
    1. Ye DATA BADALNA hai -- company ki setting badal rahi hai. Isliye
       "Allow writes" OFF ho to saaf mana kar dete hain. Chupchaap kisi ki
       company ki setting badal dena bahut galat hoga.
    2. Jo badla, wo LIKH kar rakhte hain -- taaki baad me wapas kiya ja sake
       aur report me dikhe ki test ne app ki setting chhui thi.
    """
    info = KNOWN.get(feature)
    if not info:
        raise KeyError(f"'{feature}' known settings me nahi. Ye hain: {sorted(KNOWN)}")

    row = get(feature)
    if row is None:
        capture(bp, verbose=verbose)
        row = get(feature)
    if row is None:
        raise ControlRoomNotOpen(
            f"'{feature}' Control Room me mila hi nahi. "
            f"control-room.bat chala kar poori list dekh lo.")

    # pehle se theek hai?
    already = (is_on(row.get("value")) is True and str(want).lower() in
               ("yes", "true", "on", "1")) or \
              (str(row.get("value", "")).strip().lower() == str(want).strip().lower())
    if already:
        return {"feature": feature, "changed": False,
                "value": row.get("value"), "why": "pehle se theek thi"}

    if not (settings.ALLOW_DESTRUCTIVE or SETTINGS_WRITE_OK):
        raise SettingLocked(
            f"'{feature}' abhi '{row.get('value')}' hai, chahiye '{want}'.\n"
            f"  {info['affects']}\n"
            f"  Ise badalne ke liye 'Allow writes' ON karo -- ye company ki "
            f"asli setting badalta hai, isliye bina ijazat nahi karte."
        )

    if not row.get("css"):
        raise ControlRoomNotOpen(
            f"'{feature}' ka control kahan hai, ye pata nahi. "
            f"control-room.bat dobara chalao.")

    if not open_control_room(bp, verbose=verbose):
        raise ControlRoomNotOpen("Control Room khul nahi paya")

    res = _set_control(bp, row["css"], want)
    if not res.get("ok"):
        raise ControlRoomNotOpen(
            f"'{feature}' badli nahi ja saki: {res.get('why')}")

    _save_setting(bp, verbose=verbose)
    data = read(bp, verbose=verbose)          # dobara padho -- sach yahi hai
    now = (data["settings"].get(feature) or {}).get("value")

    CHANGED.append({"feature": feature, "from": row.get("value"), "to": now,
                    "label": row.get("label", "")})
    if verbose:
        print(f"  [control room] {feature}: {row.get('value')} -> {now}")

    safety.force_close_modal(bp.page)
    return {"feature": feature, "changed": True, "from": row.get("value"),
            "value": now, "why": "badal di"}


def _save_setting(bp: BasePage, verbose: bool = False) -> dict:
    """
    Control Room ka badlav SAVE karo -- poora rasta, teen kadam.

    ASLI FLOW (user ne dekh kar bataya):
        1. Esc dabao          -> "save karna hai?" wala popup aata hai
        2. Save dabao         -> badlav lag jata hai
        3. Reload dabao       -> app naye settings ke saath dobara load hota hai

    PEHLE MAIN SIRF "Save" DHOONDHTA THA.
    ======================================
    Us waqt screen par Save tha hi nahi -- wo popup Esc dabane ke BAAD aata
    hai. Isliye 205 settings badli to gayin, par lagi nahi. Aur Reload na
    hone se app AADHURI haalat me atak gaya: uske baad koi menu mila hi
    nahi ("menu screen par nahi mila" x8), aur aakhir me browser hi band
    ho gaya.

    Yaani settings badalna kaamyab tha, par uske baad ka poora crawl mar
    gaya -- sirf isliye ki maine aakhri do kadam chhod diye the.
    """
    page = bp.page
    steps = {"escape": False, "save": False, "reload": False}

    # 1. Esc -- isse "save karein?" wala popup aata hai
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(900)
        steps["escape"] = True
    except Exception:  # noqa: BLE001
        pass

    # 2. Save -- popup ke ANDAR hai, isliye inside_modal
    # The "Save Changes ?" alert's Save is #btnYes inside div.modal-new (get_by_role does not see it).
    try:
        yb = page.locator("div.modal-new #btnYes, .modal.show #btnYes").first
        if yb.count() and yb.is_visible(timeout=1500):
            safety.guarded_click(yb, "controlroom.save:#btnYes", inside_modal=True, timeout=6000)
            wait_ready(page, timeout_ms=20000)
            steps["save"] = True
    except Exception:  # noqa: BLE001
        pass
    for label in (() if steps["save"] else ("Save", "Yes", "Save Changes", "Update")):
        try:
            b = page.get_by_role("button", name=label, exact=False).first
            if not b.count():
                b = page.get_by_text(label, exact=True).first
            if b.count() and b.is_visible(timeout=1200):
                safety.guarded_click(b, f"controlroom.save:{label}",
                                     inside_modal=True, timeout=6000)
                wait_ready(page, timeout_ms=20000)
                steps["save"] = True
                if verbose:
                    print(f"    settings save ki ('{label}')")
                break
        except Exception:  # noqa: BLE001
            continue

    # 3. Reload -- iske bina app purane settings par hi chalta rehta hai,
    #    aur menu tak gayab ho jate hain
    for label in ("Reload", "Refresh", "Reload Now", "OK"):
        try:
            b = page.get_by_role("button", name=label, exact=False).first
            if not b.count():
                b = page.get_by_text(label, exact=True).first
            if b.count() and b.is_visible(timeout=1500):
                safety.guarded_click(b, f"controlroom.reload:{label}",
                                     inside_modal=True, timeout=8000)
                steps["reload"] = True
                if verbose:
                    print(f"    app reload kiya ('{label}')")
                break
        except Exception:  # noqa: BLE001
            continue

    # An "OK" alert does not always reload the app; reload so the read-back sees what the server saved.
    if steps["save"]:
        try:
            page.reload(wait_until="domcontentloaded")
            steps["reload"] = True
        except Exception:  # noqa: BLE001
            pass
    if not steps["save"]:
        steps["note"] = "no Save button after Esc: the app did not see the change (nothing was sent)"

    # Reload ke baad app poora dobara banta hai -- uska intezaar zaroori hai,
    # warna agla kadam khali page par chalega
    try:
        page.wait_for_load_state("domcontentloaded", timeout=30000)
    except Exception:  # noqa: BLE001
        pass
    wait_ready(page, timeout_ms=30000)

    if verbose and not steps["save"]:
        print("    (Save ka button nahi mila -- kuch settings apne aap "
              "lag jati hain)")
    return steps


def wait_app_back(bp: BasePage, timeout_ms: int = 45000) -> bool:
    """
    Reload ke baad app WAAPAS aa gaya?

    Ye jaanch isliye zaroori hai ki reload ke beech me menu nahi hote. Us
    waqt crawl aage badha to har menu "nahi mila" kehta hai -- theek wahi
    hua tha, aath baar.
    """
    import time as _t
    t0 = _t.time()
    while (_t.time() - t0) * 1000 < timeout_ms:
        try:
            n = bp.page.evaluate(
                "() => document.querySelectorAll('a.menulink, #nav a').length")
            if n and n > 3:
                wait_ready(bp.page, timeout_ms=15000)
                return True
        except Exception:  # noqa: BLE001
            pass
        bp.page.wait_for_timeout(700)
    return False


# Is run me jo settings badli gayin -- report ke liye
CHANGED: list[dict] = []


def changed_report(path) -> str | None:
    if not CHANGED:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["IS RUN ME CONTROL ROOM KI YE SETTINGS BADLI GAYIN",
             "(test ke liye zaroori thin -- zarurat ho to wapas kar lo)", ""]
    for c in CHANGED:
        lines.append(f"  {c['feature']:<26} {c['from']!r} -> {c['to']!r}")
        lines.append(f"      screen par: {c['label']}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------- sab ON

BACKUP = ROOT / "config" / "control_room_backup.json"


# Jin settings ka "on" hona ON/ASK se hota hai.
# Sab chhote akshar me, kyunki MargBooks me likhawat alag-alag hai.
_ON_WORDS = ("yes", "ask")
_OFF_WORDS = ("no", "don't ask", "dont ask", "", "never")
# Kuch settings me ek teesra vikalp bhi hota hai, jaise
# "Ask Party in Retail Billing" -> Don't Ask / Ask / Ask on Spacebar.
# Ye bhi "chaalu" hi hain, isliye inhe pehchanna zaroori hai -- warna
# poori setting hi chhoot jati hai.
_EXTRA_ON = ("ask on spacebar", "always", "always ask", "on")


def on_value(row: dict) -> str | None:
    """
    Is setting ko "chaalu" karne ke liye kaunsi value chahiye?

    "Yes"  -- aam toggle ke liye
    "Ask"  -- un settings ke liye jinke vikalp Don't Ask / Ask hain
              (jaise "Ask Party in Retail Billing"). Unme "Yes" hota hi
              nahi, par unka chaalu roop "Ask" hai.
    None   -- ye Yes/No wali setting hai hi nahi.

    "Calculation Type" (Inclusive / Exclusive / Tax on MRP) ko "Yes" karna
    bemaani hai -- isliye wo None deti hai aur chhod di jati hai.
    """
    opts = [str(o).strip() for o in (row.get("options") or []) if str(o).strip()]
    if not opts:
        return None
    low = {o.lower() for o in opts}
    if not low <= set(_ON_WORDS) | set(_OFF_WORDS) | set(_EXTRA_ON):
        return None                    # koi aur tarah ki choice hai
    for want in _ON_WORDS:
        for o in opts:
            if o.lower() == want:
                return o               # jaisa likha hai waisa hi lautao
    return None


def _is_yes_no(row: dict) -> bool:
    return on_value(row) is not None


def enable_yes(bp: BasePage, only: list[str] | None = None,
               verbose: bool = True) -> dict:
    """
    Control Room ki Yes/No settings ko ON karo -- taaki har field dikhe.

    KYUN
    ----
    Bahut se field settings ke peeche chhupe hote hain. "Item Disc 1" band
    ho to wo column bill me aata hi nahi, aur crawler use kabhi nahi dekh
    payega. Un settings ko ON karke crawl karne se POORA naksha milta hai.

    KHATRA -- aur ye chhupana nahi chahiye
    --------------------------------------
    Ye asli company ki settings BADALTA hai. 557 dropdown sab ON karne se:
      - har jagah mandatory field lag jayenge (Patient, Doctor, MR)
      - har form pe popup aane lagenge
      - crawl AASAN nahi, MUSHKIL ho jayega

    Isliye:
      only=[...]  -> sirf wahi settings jo field dikhane se judi hain (default)
      only=None   -> saari Yes/No settings (poora sweep -- soch kar)

    Badalne se PEHLE purani haalat backup me likhi jati hai, aur
    restore-settings.bat se wapas ki ja sakti hai.
    """
    if not (settings.ALLOW_DESTRUCTIVE or SETTINGS_WRITE_OK):
        raise SettingLocked(
            "Settings badalne ke liye 'Allow writes' ON karna padega.\n"
            "  Ye company ki asli setting badalta hai, isliye bina ijazat nahi."
        )

    if not open_control_room(bp, verbose=verbose):
        raise ControlRoomNotOpen("Control Room khul nahi paya")
    data = read(bp, verbose=False)

    rows = data.get("raw", [])
    wanted_labels = None
    if only is not None:
        wanted_labels = set()
        for name in only:
            for lab in (KNOWN.get(name, {}).get("labels") or []):
                wanted_labels.add(_norm_label(lab))

    todo = []
    for r in rows:
        if not _is_yes_no(r):
            continue
        want = on_value(r)
        if str(r.get("value", "")).strip().lower() == str(want).lower():
            continue                      # pehle se ON
        if wanted_labels is not None and _norm_label(r["label"]) not in wanted_labels:
            continue
        if not r.get("css"):
            continue
        todo.append(r)

    # Purani haalat pehle likho -- badalne se PEHLE
    before = [{"label": r["label"], "css": r["css"], "was": r.get("value", "")}
              for r in todo]
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    BACKUP.write_text(json.dumps(
        {"saved_at": time.strftime("%Y-%m-%d %H:%M"), "settings": before},
        indent=1, ensure_ascii=False), encoding="utf-8")

    if verbose:
        print(f"    {len(todo)} setting badalni hain "
              f"({sum(1 for r in rows if _is_yes_no(r))} me se -- baaki "
              f"pehle se ON hain)")
        if len(todo) > 50:
            print(f"    Isme kuch minute lagenge. Har 25 par ginti dikhegi.")

    changed, failed = [], []
    for i, r in enumerate(todo, 1):
        try:
            res = _set_control(bp, r["css"], on_value(r) or "Yes")
            if res.get("ok") and res.get("changed"):
                changed.append({"label": r["label"], "from": r.get("value"),
                                "to": res.get("now")})
                if verbose and (len(todo) <= 40 or i % 25 == 0 or i == len(todo)):
                    print(f"    [{i}/{len(todo)}] {r['label'][:44]}: "
                          f"{r.get('value')} -> {res.get('now')}")
            elif not res.get("ok"):
                failed.append({"label": r["label"], "why": res.get("why", "")})
        except Exception as e:  # noqa: BLE001
            failed.append({"label": r["label"], "why": str(e)[:120]})

    back = True
    if changed:
        steps = _save_setting(bp, verbose=verbose)
        back = wait_app_back(bp)
        if verbose:
            print(f"    save={steps['save']} reload={steps['reload']} "
                  f"app-wapas={back}")
    safety.force_close_modal(bp.page)

    CHANGED.extend(changed)
    return {"total_yes_no": sum(1 for r in rows if _is_yes_no(r)),
            "tried": len(todo), "changed": len(changed),
            "failed": len(failed), "details": changed, "problems": failed,
            "app_back": back, "backup": str(BACKUP)}


def _norm_label(t: str) -> str:
    return "".join(ch for ch in str(t).lower() if ch.isalnum())


def restore(bp: BasePage, verbose: bool = True) -> dict:
    """
    Backup se settings wapas laao.

    Crawl ke liye badli hui settings company me hamesha ke liye nahi rehni
    chahiye -- warna kal koi asli kaam karega aur socha kuch aur hoga.
    """
    if not BACKUP.exists():
        return {"error": "koi backup nahi mila -- kuch badla hi nahi tha"}
    if not (settings.ALLOW_DESTRUCTIVE or SETTINGS_WRITE_OK):
        raise SettingLocked("Wapas karne ke liye bhi 'Allow writes' chahiye")

    saved = json.loads(BACKUP.read_text(encoding="utf-8"))
    if not open_control_room(bp, verbose=verbose):
        raise ControlRoomNotOpen("Control Room khul nahi paya")

    back, failed = [], []
    for r in saved.get("settings", []):
        try:
            res = _set_control(bp, r["css"], r["was"])
            if res.get("ok"):
                back.append(r["label"])
                if verbose:
                    print(f"    {r['label'][:44]}: -> {r['was']}")
            else:
                failed.append({"label": r["label"], "why": res.get("why")})
        except Exception as e:  # noqa: BLE001
            failed.append({"label": r["label"], "why": str(e)[:120]})

    if back:
        _save_setting(bp, verbose=verbose)
        wait_app_back(bp)          # reload ke baad app wapas aane do
    safety.force_close_modal(bp.page)
    return {"restored": len(back), "failed": len(failed),
            "saved_at": saved.get("saved_at"), "problems": failed}


def summary() -> str:
    d = load()
    if not d.get("read_at"):
        return "Control Room abhi padha nahi gaya"
    on = [k for k, v in d["settings"].items() if v.get("on") is True]
    off = [k for k, v in d["settings"].items() if v.get("on") is False]
    ch = [f"{k}={v['value']}" for k, v in d["settings"].items()
          if v.get("kind") == "choice"]
    parts = [f"{d['total']} settings ({d['read_at']})"]
    if on:
        parts.append("ON: " + ", ".join(on))
    if off:
        parts.append("OFF: " + ", ".join(off))
    if ch:
        parts.append(", ".join(ch))
    return " | ".join(parts)


def choice(feature: str) -> str | None:
    """Choice wali setting ki abhi ki value -- jaise 'Inclusive'."""
    row = get(feature)
    return row.get("value") if row else None


def expect_choice(feature: str, want: str):
    """
    Test likh sakta hai: "ye test tab hi lagu hai jab Calculation Inclusive ho".
    Alag value ho to FeatureOff -- SKIP, kyunki app theek hai.
    """
    row = get(feature)
    if row is None:
        raise FeatureOff(f"'{feature}' abhi padha nahi gaya -- "
                         f"control-room.bat chala do")
    got = str(row.get("value", "")).strip().lower()
    if got != str(want).strip().lower():
        raise FeatureOff(
            f"Ye test '{feature} = {want}' ke liye hai, par is company me "
            f"'{row.get('value')}' set hai.\n"
            f"  {row.get('affects')}\n"
            f"  Ye bug NAHI hai.")


def report(path) -> str | None:
    d = load()
    if not d.get("read_at"):
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"CONTROL ROOM -- {d['read_at']}",
             f"{d['total']} settings padhi gayin", "",
             "--- jo humare tests par asar daalti hain ---"]
    for k, v in d["settings"].items():
        if v.get("kind") == "choice":
            state = "SET"          # choice hai -- ON/OFF ka sawaal hi nahi
        elif v.get("on") is True:
            state = "ON "
        elif v.get("on") is False:
            state = "OFF"
        else:
            state = "?  "
        lines.append(f"  [{state}] {k:<26} {v['label']} = {v['value']}")
        lines.append(f"          {v['affects']}")
        if v.get("options"):
            lines.append(f"          ho sakta hai: {' / '.join(v['options'][:6])}")
    lines += ["", "--- baaki saari settings ---"]
    for r in d.get("raw", []):
        lines.append(f"  {r['label'][:48]:<48} = {r['value']}"
                     + (f"   ({'/'.join(r['options'][:4])})" if r.get("options") else ""))
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


# ------------------------------------------------------------ any setting, by its label

def _rows_live(bp: BasePage) -> list[dict]:
    # Right after a settings save the app reloads; the panel can open before its rows are drawn and the scan
    # then sees none ("No Control Room setting labelled 'M.R.Master'. Close labels: []", TC_SALE_212).
    # Wait for the rows instead of reading an empty panel.
    rows: list[dict] = []
    for attempt in range(8):
        wait_ready(bp.page, timeout_ms=20000)
        raw = bp.page.evaluate(SCAN_JS)
        rows = [r for r in raw.get("settings", []) if not r.get("hidden")]
        if len(rows) > 50:
            return rows
        bp.page.wait_for_timeout(1500)
        if attempt == 4 and not rows:
            # a half-closed panel (rows hidden) still "looks like" the Control Room: start again from the dashboard
            try:
                safety.force_close_modal(bp.page)
                bp.goto(f"{settings.BASE_URL}/dashboard", check_auth=False)
                bp.page.wait_for_timeout(2500)
            except Exception:  # noqa: BLE001
                pass
            open_control_room(bp)
    return rows


def _pick_row(rows: list[dict], label: str, nth: int | None = None) -> dict:
    # "Control Room > Sale BackDate Billing" (a path written in the case): the setting is the last part
    label = re.sub(r"^.*>\s*", "", str(label)) if ">" in str(label) else label
    want = _norm_label(label)
    if not want:
        raise ControlRoomNotOpen(f"empty setting label {label!r}")
    hits = [r for r in rows if _norm_label(r.get("label", "")) == want]
    if not hits:
        hits = [r for r in rows if want in _norm_label(r.get("label", ""))]
    if not hits:
        words = {w for w in re.findall(r"[a-z0-9]+", label.lower()) if len(w) > 3}
        near = sorted({r["label"] for r in rows if words & set(re.findall(r"[a-z0-9]+", r["label"].lower()))})[:8]
        raise ControlRoomNotOpen(f"No Control Room setting labelled {label!r}. Close labels: {near}")
    if len(hits) > 1 and nth is None:
        raise ControlRoomNotOpen(
            f"{len(hits)} settings match {label!r}: " + "; ".join(f"{r['label']} [{r['css']}]" for r in hits[:6])
            + ". Use the exact label, or 'Label #2' for the second one.")
    return hits[(nth or 1) - 1]


# Settings the app cannot turn back once changed (the company's data is converted): never changed by a test run.
ONE_WAY = ("pos?", "pos", "multi unit required in sale", "multi unit required in purchase", "multi unit")


def _is_one_way(label: str) -> bool:
    n = _norm_label(label).rstrip("?").strip()
    return any(n == _norm_label(x).rstrip("?").strip() for x in ONE_WAY)


def _split_nth(label: str) -> tuple[str, int | None]:
    m = re.match(r"(.+?)\s*#(\d+)$", label.strip())
    return (m.group(1), int(m.group(2))) if m else (label.strip(), None)


def read_setting(bp: BasePage, label: str) -> dict:
    """Current value of one Control Room setting, read live (nothing changed)."""
    if (cp := _config_path(label)):
        try:
            return read_config_setting(bp, *cp)
        except ControlRoomNotOpen as e:
            if "with a Configure button" not in str(e):
                raise
    lab, nth = _split_nth(label)
    if not open_control_room(bp):
        raise ControlRoomNotOpen("Control Room khul nahi paya")
    try:
        r = _pick_row(_rows_live(bp), lab, nth)
    finally:
        safety.force_close_modal(bp.page)
    return {"label": r["label"], "value": r.get("value", ""), "options": r.get("options", []), "css": r["css"]}


def set_setting(bp: BasePage, label: str, want: str) -> dict:
    """
    Set ANY Control Room setting by its label (548 of them, not just the KNOWN list), save, reload, read back.
    Only in a QA test company (framework.qa_company): settings are company data.
    """
    from framework import qa_company
    qa_company.require_test_company(bp.page, f"change setting {label!r}")
    if (cp := _config_path(label)):          # "Loss Indication > Net Loss ...?": a field in a row's Configure window
        try:
            return set_config_setting(bp, *cp, want)
        except ControlRoomNotOpen as e:
            if "with a Configure button" not in str(e):
                raise
    lab, nth = _split_nth(label)
    if not open_control_room(bp):
        raise ControlRoomNotOpen("Control Room khul nahi paya")
    r = _pick_row(_rows_live(bp), lab, nth)
    before = r.get("value", "")
    if str(before).strip().lower() == str(want).strip().lower():
        safety.force_close_modal(bp.page)
        return {"label": r["label"], "changed": False, "value": before}
    if _is_one_way(r["label"]) and not os.environ.get("ALLOW_ONE_WAY_SETTINGS"):
        safety.force_close_modal(bp.page)
        raise SettingLocked(f"{r['label']!r} cannot be turned back once changed (it converts the company's data), "
                            f"so the tool does not change it ({before!r} -> {want!r}). Set it by hand in a QA company "
                            f"made for it, or run with ALLOW_ONE_WAY_SETTINGS=1 after agreeing to it.")
    res = _set_control(bp, r["css"], want)
    if not res.get("ok"):
        safety.force_close_modal(bp.page)
        raise ControlRoomNotOpen(f"{r['label']!r} could not be set to {want!r}: {res.get('why')}")
    msgs_before = len(safety.get_toasts(bp.page))
    saved = _save_setting(bp) if res.get("changed", True) else {"save": True}
    toasts = [t.get("text", t) if isinstance(t, dict) else t for t in safety.get_toasts(bp.page)[msgs_before:]]
    if not open_control_room(bp):
        raise ControlRoomNotOpen("Control Room did not reopen to check the saved value")
    try:
        now = next((x.get("value", "") for x in _rows_live(bp) if x["css"] == r["css"]), None)
    finally:
        safety.force_close_modal(bp.page)
    CHANGED.append({"feature": r["label"], "from": before, "to": now, "label": r["label"]})
    if str(now).strip().lower() != str(want).strip().lower():
        raise ControlRoomNotOpen(f"{r['label']!r}: asked {want!r}, after save it is {now!r}. App said: {toasts[:3]}. "
                                 f"Save flow: {saved}")
    return {"label": r["label"], "changed": True, "from": before, "value": now}


# ---------- settings behind a row's own Configure button ----------
# Some Control Room rows have no value of their own but a "Configure" button that opens a small window with the
# real settings, e.g.  Loss Indication -> "Net Loss and Margin Loss Indication Required?" (Indicate / Forcefully).
# Cases write them as a path:  "Loss Indication > Net Loss and Margin Loss Indication Required?"  (TC_SALE_203).

CONFIG_FIELDS_JS = r"""() => {
  const m = [...document.querySelectorAll('ngb-modal-window, .modal.show')].filter(e => e.getClientRects().length).pop();
  if (!m) return null;
  const title = ((m.querySelector('.modal-title, .modal-header, h4, h5') || {}).innerText || '').trim();
  const out = [];
  [...m.querySelectorAll('select, input[type=checkbox]')].filter(e => e.getClientRects().length).forEach((e, i) => {
    let r = e, label = '';
    for (let k = 0; k < 5 && r.parentElement; k++) {
      r = r.parentElement;
      label = (r.innerText || '').replace(e.innerText || '', '').trim();
      if (label) break;
    }
    if (!e.id) e.setAttribute('data-mbcfg', String(i));
    out.push({css: e.id ? '#' + e.id : `[data-mbcfg="${i}"]`, tag: e.tagName.toLowerCase(), label: label.split('\n')[0].trim(),
              value: e.tagName === 'SELECT' ? ((e.options[e.selectedIndex] || {}).text || '') : (e.checked ? 'Yes' : 'No'),
              options: e.tagName === 'SELECT' ? [...e.options].map(o => o.text) : ['No', 'Yes']});
  });
  return {title, fields: out};
}"""


def _config_path(label: str) -> tuple[str, str] | None:
    """'Control Room > Loss Indication (Configure) > Net Loss ...?' -> ('Loss Indication', 'Net Loss ...?')."""
    parts = [re.sub(r"\(\s*configure\s*\)", "", p, flags=re.I).strip() for p in str(label).split(">")]
    parts = [p for p in parts if p and p.lower() != "control room"]
    return (parts[-2], parts[-1]) if len(parts) >= 2 else None


def _open_row_configure(bp: BasePage, row_label: str) -> bool:
    page = bp.page
    rows = page.locator(f"xpath=//div[contains(@class,'row')][./div[normalize-space()={_xq(row_label)}]]"
                        f"[.//button[normalize-space()='Configure']]")
    for i in range(min(rows.count(), 10)):
        r = rows.nth(i)
        if not r.is_visible():
            continue
        btn = r.locator("xpath=.//button[normalize-space()='Configure']").first
        btn.scroll_into_view_if_needed(timeout=5000)
        safety.guarded_click(btn, f"controlroom.configure:{row_label}", inside_modal=True)
        for _ in range(20):
            page.wait_for_timeout(250)
            info = page.evaluate(CONFIG_FIELDS_JS)
            if info and info.get("fields"):
                return True
        return False
    return False


def _xq(s: str) -> str:
    """XPath string literal."""
    if "'" not in s:
        return f"'{s}'"
    if '"' not in s:
        return f'"{s}"'
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in s.split("'")) + ")"


def _config_field(bp: BasePage, field_label: str) -> dict:
    info = bp.page.evaluate(CONFIG_FIELDS_JS) or {}
    want = _norm_label(field_label)
    fields = info.get("fields", [])
    hit = [f for f in fields if _norm_label(f["label"]) == want] or \
          [f for f in fields if want and (want in _norm_label(f["label"]) or _norm_label(f["label"]) in want)]
    if not hit:
        raise ControlRoomNotOpen(f"No field {field_label!r} in the {info.get('title')!r} window. "
                                 f"Fields: {[f['label'] for f in fields]}")
    return hit[0]


def read_config_setting(bp: BasePage, row_label: str, field_label: str) -> dict:
    if not open_control_room(bp):
        raise ControlRoomNotOpen("Control Room khul nahi paya")
    try:
        if not _open_row_configure(bp, row_label):
            raise ControlRoomNotOpen(f"No Control Room row {row_label!r} with a Configure button")
        f = _config_field(bp, field_label)
        return {"label": f"{row_label} > {f['label']}", "value": f["value"], "options": f["options"], "css": f["css"]}
    finally:
        safety.force_close_modal(bp.page)
        safety.force_close_modal(bp.page)


def set_config_setting(bp: BasePage, row_label: str, field_label: str, want: str) -> dict:
    from framework import qa_company
    qa_company.require_test_company(bp.page, f"change setting {row_label} > {field_label}")
    if not open_control_room(bp):
        raise ControlRoomNotOpen("Control Room khul nahi paya")
    try:
        if not _open_row_configure(bp, row_label):
            raise ControlRoomNotOpen(f"No Control Room row {row_label!r} with a Configure button")
        f = _config_field(bp, field_label)
        label = f"{row_label} > {f['label']}"
        before = f["value"]
        if before.strip().lower() == str(want).strip().lower():
            return {"label": label, "changed": False, "value": before}
        res = _set_control(bp, f["css"], want)
        if not res.get("ok"):
            raise ControlRoomNotOpen(f"{label!r} could not be set to {want!r}: {res.get('why')}")
        page = bp.page
        save = page.locator("xpath=(//ngb-modal-window | //div[contains(@class,'modal') and contains(@class,'show')])"
                            "[last()]//button[contains(normalize-space(),'Save')]").first
        safety.guarded_click(save, f"controlroom.configure.save:{row_label}", inside_modal=True)
        page.wait_for_timeout(1500)
        for txt in ("Yes", "Ok", "OK"):                 # a confirm after the save, if the app asks
            b = page.locator(f"xpath=//ngb-modal-window//button[normalize-space()='{txt}']")
            if b.count() and b.first.is_visible():
                safety.guarded_click(b.first, f"controlroom.configure.confirm:{txt}", inside_modal=True)
                page.wait_for_timeout(1500)
                break
        wait_app_back(bp)
    finally:
        safety.force_close_modal(bp.page)
        safety.force_close_modal(bp.page)
    now = read_config_setting(bp, row_label, field_label)["value"]
    CHANGED.append({"feature": label, "from": before, "to": now, "label": label})
    if now.strip().lower() != str(want).strip().lower():
        raise ControlRoomNotOpen(f"{label!r}: asked {want!r}, after save it is {now!r}")
    return {"label": label, "changed": True, "from": before, "value": now}
