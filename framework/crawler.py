"""
MargBooks ka poora UI crawler -- menu se menu, kram se.

KYA KARTA HAI
-------------
Login karta hai, phir menu_sequence.json ke KRAM me har menu -> submenu
kholta hai, page ke sach me taiyaar hone ka intezaar karta hai, uske saare
element (id, CSS, XPath, label, placeholder, dropdown ke vikalp) nikaalta
hai, aur HAR PAGE KE BAAD turant save kar deta hai.

KYUN "KRAM SE", "DHOONDH KAR" NAHI
----------------------------------
"Saare link dhoondho aur click karo" wala tareeka yahan kaam nahi karta.
Angular menu ko har baar alag kram me render karta hai, aur kuch link app
se bahar le jate hain. Ek fix kram se chalne ka matlab hai: har run me wahi
natija, aur agar koi menu na mile to wo SAAF dikhega -- chupchaap chhootega
nahi.

READ-ONLY
---------
Ye kuch banata ya badalta NAHI hai. Bill save nahi karta, master nahi
banata, Control Room ki setting nahi badalta. Dropdown kholta hai sirf
vikalp padhne ke liye, aur turant band kar deta hai.

Iske liye poore crawl me ALLOW_DESTRUCTIVE band rehta hai -- chahe UI me
"Allow writes" ON ho. Scanner ka kaam dekhna hai, chhoona nahi.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from config.settings import ROOT, settings
from framework import logbook, safety
from framework.base_page import BasePage
from framework.page_ready import wait_ready

OUT = ROOT / "crawler-output"
SEQ_FILE = ROOT / "config" / "menu_sequence.json"

# Har cheez ka ek haal hota hai. Chupchaap chhodna mana hai.
PENDING, RUNNING, PASS, FAILED, BLOCKED, SKIPPED, PARTIAL = (
    "PENDING", "RUNNING", "PASS", "FAILED", "BLOCKED", "SKIPPED_BY_CONFIG",
    "PARTIAL")


# ---------------------------------------------------------------- extract
#
# Pehle extract() sirf <input>, <select>, <button>, <a href>, <table> dekhta tha.
# Nakli page par jaanch me ye sab CHHOOT jate the:
#   - div / span / i par click handler (Angular ka (click)) -- 355 jagah source me
#   - <a> bina href -- 225 jagah
#   - custom dropdown (ng-select jaisa)
#   - tab ke headers, aur dusre tab ke andar ke field (*ngIf: 4782 jagah)
#   - ag-Grid ke wo column jo scroll se bahar the
#   - iframe aur shadow DOM ke andar ke element
#
# Ab ek ya do chiz DOM me dikhne se bahar bhi hain (popup, dropdown badalne par
# aane wale field) -- unke liye collect() neeche hai. extract() sirf EK baar ka
# snapshot hai; collect() uske upar poora kaam karta hai.

EXTRACT_JS = r"""
() => {
  const norm = t => (t || '').replace(/\s+/g, ' ').trim();

  // Open shadow root ke andar bhi dhoondho. Roots ek hi baar jama karte hain.
  const roots = [document];
  for (let i = 0; i < roots.length; i++) {
    roots[i].querySelectorAll('*').forEach(h => {
      if (h.shadowRoot) roots.push(h.shadowRoot);
    });
  }
  const all = sel => roots.flatMap(r => [...r.querySelectorAll(sel)]);

  const MODAL = '.modal, [role="dialog"], ngb-modal-window, .swal2-popup, '
              + '.ui-dialog, .cdk-overlay-pane, .mat-dialog-container';
  const CHROME = '#ul_id, nav, .sidebar, header, .navbar';
  const DANGER = /(del(ete)?|trash|remove|discard|destroy|erase|purge|void)/i;
  const inModal = el => !!el.closest(MODAL);
  const inChrome = el => !!el.closest(CHROME);

  const cssOf = (el) => {
    if (el.id && /^[A-Za-z][\w-]*$/.test(el.id))
      return `${el.tagName.toLowerCase()}#${el.id}`;
    for (const a of ['data-testid', 'formcontrolname', 'name', 'aria-label',
                     'placeholder']) {
      const v = el.getAttribute(a);
      if (v) return `${el.tagName.toLowerCase()}[${a}="${v.replace(/"/g,'')}"]`;
    }
    const t = norm(el.innerText);
    if (t && t.length < 30) return `${el.tagName.toLowerCase()}:has-text("${t}")`;
    return '';
  };

  // Absolute XPath sirf tab jab aur koi pehchan na ho. Wo page ke dhaanche
  // se bandha hota hai aur ek div badalne se toot jata hai.
  const xpathOf = (el) => {
    if (el.id && /^[A-Za-z][\w-]*$/.test(el.id)) return `//*[@id="${el.id}"]`;
    for (const a of ['data-testid', 'formcontrolname', 'name']) {
      const v = el.getAttribute(a);
      if (v) return `//${el.tagName.toLowerCase()}[@${a}="${v}"]`;
    }
    const parts = [];
    let n = el;
    while (n && n.nodeType === 1 && n.tagName !== 'BODY') {
      const sibs = [...(n.parentElement ? n.parentElement.children : [])]
        .filter(c => c.tagName === n.tagName);
      parts.unshift(n.tagName.toLowerCase()
        + (sibs.length > 1 ? `[${sibs.indexOf(n) + 1}]` : ''));
      n = n.parentElement;
    }
    return '/html/body/' + parts.join('/');
  };

  const labelOf = (el) => {
    if (el.id) {
      const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (l && norm(l.innerText)) return norm(l.innerText);
    }
    const ab = el.getAttribute('aria-labelledby');
    if (ab) {
      const t = document.getElementById(ab);
      if (t) return norm(t.innerText);
    }
    if (el.getAttribute('aria-label')) return norm(el.getAttribute('aria-label'));
    let box = el.parentElement;
    for (let i = 0; box && i < 4; i++, box = box.parentElement) {
      const c = [...box.querySelectorAll('label,span,td,th,div,p')]
        .find(x => x.children.length === 0 && !x.contains(el)
                   && norm(x.innerText).length > 1
                   && norm(x.innerText).length < 45
                   && !/^\d+$/.test(norm(x.innerText)));
      if (c) return norm(c.innerText);
    }
    return '';
  };

  const state = (el) => {
    const r = el.getBoundingClientRect();
    return {
      visible: r.width > 0 && r.height > 0,
      inView: r.width > 0 && r.top < innerHeight && r.bottom > 0,
      enabled: !el.disabled,
      editable: !el.disabled && !el.readOnly,
      checked: el.checked === undefined ? null : !!el.checked,
    };
  };

  // tab / accordion jaise control ko ek pakki pehchan do, taaki baad me
  // (collect me) usi par click ho sake -- text se nahi.
  const tag = (el, p) => {
    let u = el.getAttribute('data-qa-uid');
    if (!u) {
      window.__qaUid = (window.__qaUid || 0) + 1;
      u = p + window.__qaUid;
      el.setAttribute('data-qa-uid', u);
    }
    return u;
  };

  const base = (el, kind) => {
    const bag = [el.id, typeof el.className === 'string' ? el.className : '',
                 el.getAttribute('title') || '', el.getAttribute('aria-label') || '',
                 norm(el.innerText).slice(0, 25)].join(' ');
    return {
      elementType: kind,
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      id: el.id || '',
      name: el.getAttribute('name') || '',
      formControlName: el.getAttribute('formcontrolname') || '',
      testId: el.getAttribute('data-testid') || '',
      placeholder: el.getAttribute('placeholder') || '',
      ariaLabel: el.getAttribute('aria-label') || '',
      title: el.getAttribute('title') || '',
      role: el.getAttribute('role') || '',
      text: norm(el.innerText).slice(0, 60),
      label: labelOf(el),
      cssSelector: cssOf(el),
      xpath: xpathOf(el),
      inModal: inModal(el),
      inChrome: inChrome(el),
      danger: DANGER.test(bag),
      ...state(el),
    };
  };

  const out = {inputs: [], buttons: [], dropdowns: [], checkboxes: [],
               links: [], tables: [], clickables: [], customSelects: [],
               tabs: [], collapsers: [], gridColumns: [], gridScroll: []};

  const handled = new Set();     // jo pehle se kisi group me aa chuka

  all('input, textarea').forEach(el => {
    const t = (el.getAttribute('type') || 'text').toLowerCase();
    if (t === 'hidden') return;
    handled.add(el);
    if (t === 'checkbox' || t === 'radio') out.checkboxes.push(base(el, t));
    else out.inputs.push(base(el, 'input'));
  });

  all('select').forEach(el => {
    handled.add(el);
    const row = base(el, 'dropdown');
    row.currentValue = (el.options[el.selectedIndex] || {}).text || '';
    // 60 par rukna galat tha -- lambi list ke aakhri vikalp chhoot jate the.
    row.options = [...el.options].map(o => ({
      text: norm(o.text), value: o.value})).slice(0, 300);
    row.optionCount = el.options.length;
    out.dropdowns.push(row);
  });

  all('button, [role="button"], input[type=button], input[type=submit]')
    .forEach(el => { handled.add(el); out.buttons.push(base(el, 'button')); });

  all('a[href]').forEach(el => {
    handled.add(el);
    const href = el.getAttribute('href') || '';
    // App ke bahar wale link crawl nahi karte.
    //
    // Pehle ye href.includes(hostname) se hota tha -- kachcha tareeka:
    // "example.com/?x=books6.margbooks.com" bhi apna lagta, aur jahan
    // hostname khali ho wahan har link apna ban jata. Ab host milate hain.
    if (/^https?:\/\//i.test(href)) {
      let host = '';
      try { host = new URL(href, location.href).hostname; } catch (e) { return; }
      if (!host || host !== location.hostname) return;
    }
    out.links.push({...base(el, 'link'), href});
  });

  all('table').forEach((el, i) => {
    const heads = [...el.querySelectorAll('th')].map(h => norm(h.innerText))
      .filter(Boolean);
    if (heads.length) out.tables.push({index: i, headers: heads.slice(0, 120),
                                       rows: el.querySelectorAll('tr').length});
  });

  // ag-Grid <table> nahi hota -- uske column alag se. Ye sirf WO column hain
  // jo abhi DOM me bane hain (ag-Grid bahar wale column banata hi nahi);
  // baaki collect() scroll karke nikalta hai.
  const colIds = new Map();
  all('[role="columnheader"][col-id], .ag-header-cell[col-id]').forEach(h =>
    colIds.set(h.getAttribute('col-id'), norm(h.innerText)));
  all('[role="row"] [col-id]').forEach(c => {
    const id = c.getAttribute('col-id');
    if (id && !colIds.has(id)) colIds.set(id, '');
  });
  const agCols = [...colIds].map(([id, label]) => ({id, label}));
  out.gridColumns = agCols;
  if (agCols.length) out.tables.push({index: -1, agGrid: true,
                                      headers: agCols.map(c => c.label),
                                      columns: agCols});
  out.gridScroll = all('.ag-center-cols-viewport').map((v, i) =>
    ({index: i, scrollWidth: v.scrollWidth, clientWidth: v.clientWidth}));

  // ---- click wali cheezein jo <button>/<a href> nahi hain ----
  const SEMANTIC = '[onclick], [role=tab], [role=menuitem], [role=option], '
    + '[role=switch], [role=link], [role=treeitem], a:not([href]), '
    + '[data-toggle], [data-bs-toggle], [tabindex]';
  const POINTER_TAGS = 'div,span,i,li,td,th,img,svg,label,p,em,b,mat-icon';
  const seen = new Set();
  const visible = el => { const r = el.getBoundingClientRect();
                          return r.width > 0 && r.height > 0; };
  const covered = el => { const p = el.parentElement &&
                            el.parentElement.closest('button, a[href], [role="button"]');
                          return !!p; };
  const cands = all(SEMANTIC);
  // Angular (click) DOM me dikhta nahi (listener JS me lagta hai). Par
  // cursor:pointer dikhta hai -- aur wo CSS se bacchon me bhi utarta hai, isliye
  // sirf sabse upar wala (jiska parent pointer nahi) lete hain.
  const ptr = e => getComputedStyle(e).cursor === 'pointer';
  all(POINTER_TAGS).slice(0, 8000).forEach(e => {
    if (!visible(e)) return;
    if (ptr(e) && !(e.parentElement && ptr(e.parentElement))) cands.push(e);
  });
  cands.forEach(el => {
    if (seen.has(el) || handled.has(el)) return;
    seen.add(el);
    if (!visible(el) || inChrome(el) || covered(el)) return;
    const ti = el.getAttribute('tabindex');
    if (ti === '-1') return;
    if (['INPUT', 'SELECT', 'TEXTAREA', 'BUTTON'].includes(el.tagName)) return;
    out.clickables.push({...base(el, 'clickable'),
                         href: el.getAttribute('href') || ''});
  });

  // ---- custom dropdown (ng-select, mat-select, select2 ...) ----
  const CUSTOM = 'ng-select, .ng-select, mat-select, p-dropdown, '
    + '.select2-container, angular2-multiselect, ng-multiselect-dropdown, '
    + '[role=combobox], [role=listbox]';
  const csSeen = new Set();
  all(CUSTOM).forEach(el => {
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName)) return;
    if (!visible(el) || inChrome(el) || csSeen.has(el)) return;
    if (el.parentElement && el.parentElement.closest(CUSTOM)) return;
    csSeen.add(el);
    const val = el.querySelector('.ng-value-label, .ng-value, .mat-select-value, '
      + '.select2-selection__rendered, [class*="value"]');
    out.customSelects.push({...base(el, 'customSelect'),
                            value: norm((val || el).innerText).slice(0, 60),
                            uid: tag(el, 'cs')});
  });

  // ---- tab ke header ----
  const TAB = '[role=tab], .nav-tabs a, .nav-tabs .nav-link, ul.nav-pills a, '
    + 'ngb-nav .nav-link, .mat-tab-label, .mat-mdc-tab, [data-toggle=tab], '
    + '[data-bs-toggle=tab], .tab-header, .p-tabview-nav a, .ui-tabview-nav a';
  const tabSeen = new Set();
  all(TAB).forEach(el => {
    if (tabSeen.has(el) || !visible(el) || inChrome(el)) return;
    tabSeen.add(el);
    const li = el.closest('li');
    const active = el.classList.contains('active')
      || el.getAttribute('aria-selected') === 'true'
      || el.classList.contains('mat-tab-label-active')
      || el.classList.contains('mdc-tab--active')
      || !!(li && li.classList.contains('active'));
    out.tabs.push({...base(el, 'tab'), active, href: el.getAttribute('href') || '',
                   uid: tag(el, 'tab')});
  });

  // ---- accordion / collapse ke header ----
  const COLL = '[data-toggle=collapse], [data-bs-toggle=collapse], '
    + '.accordion-button, .mat-expansion-panel-header, summary, '
    + 'ngb-accordion .card-header a, '
    + '[aria-expanded="false"]:not(.dropdown-toggle):not([data-toggle=dropdown])';
  const collSeen = new Set();
  all(COLL).forEach(el => {
    if (collSeen.has(el) || !visible(el) || inChrome(el)) return;
    if (el.closest('[role=tablist], .nav-tabs')) return;       // tab hai, accordion nahi
    collSeen.add(el);
    const ae = el.getAttribute('aria-expanded');
    const expanded = ae === 'true'
      || (el.tagName === 'SUMMARY' && !!(el.parentElement && el.parentElement.open))
      || (ae === null && !el.classList.contains('collapsed'));
    out.collapsers.push({...base(el, 'collapser'), expanded,
                         href: el.getAttribute('href') || '',
                         uid: tag(el, 'col')});
  });

  const bodyText = norm((document.body || {}).innerText || '');
  return {
    ...out,
    page: {
      url: location.href,
      title: document.title,
      heading: norm((document.querySelector('h1, .mhead, .pageTitle') || {})
                     .innerText || '').slice(0, 80),
      // Adhoora/galat page pehchanne ke liye (Sign In, "not authorized")
      bodyHint: bodyText.slice(0, 400).toLowerCase(),
      bodyLength: bodyText.length,
    },
  };
}
"""

GRID_COLS_JS = r"""
() => {
  const norm = t => (t || '').replace(/\s+/g, ' ').trim();
  const m = new Map();
  document.querySelectorAll('[role="columnheader"][col-id], .ag-header-cell[col-id]')
    .forEach(h => m.set(h.getAttribute('col-id'), norm(h.innerText)));
  document.querySelectorAll('[role="row"] [col-id]').forEach(c => {
    const id = c.getAttribute('col-id');
    if (id && !m.has(id)) m.set(id, '');
  });
  return [...m].map(([id, label]) => ({id, label}));
}
"""

# Grid ko seedha seedha scroll karo (side me) -- sirf dekhne ke liye, koi click nahi.
GRID_SCROLL_JS = r"""
async ([i, x]) => {
  const v = document.querySelectorAll('.ag-center-cols-viewport')[i];
  if (v) v.scrollLeft = x;
  const h = document.querySelectorAll('.ag-header-viewport')[i];
  if (h) h.scrollLeft = x;
  // scroll ka event aur uske baad ag-Grid ka render ek-do frame me hota hai --
  // fixed 160ms par bharosa karna bhaari page par kam pad jata tha.
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  return v ? v.scrollLeft : -1;
}
"""

# Dropdown ka vikalp badlo -- SIRF form ki haalat. Kuch save nahi hota, aur
# form bina save kiye band hota hai. Text se vikalp chunte hain (value kai
# vikalpo me ek jaisi ho sakti hai).
SET_SELECT_JS = r"""
([sel, text]) => {
  const e = document.querySelector(sel);
  if (!e) return false;
  const o = [...e.options].find(x => (x.text || '').replace(/\s+/g, ' ').trim() === text);
  if (!o) return false;
  e.value = o.value;
  e.dispatchEvent(new Event('input',  {bubbles: true}));
  e.dispatchEvent(new Event('change', {bubbles: true}));
  return true;
}
"""

# collect() jin group ko jodta hai
LIST_KEYS = ("inputs", "buttons", "dropdowns", "checkboxes", "links",
             "clickables", "customSelects", "tabs", "collapsers")

# Itne se kam element = shak. Asli MargBooks page me kam se kam ek search/button/
# menu hota hi hai.
MIN_ELEMENTS = 3

# In ko tab/accordion samajh kar bhi KABHI nahi dabate.
STATE_BLOCK = ("save", "f10", "submit", "post", "confirm", "delete", "remove",
               "print", "logout", "log out", "sign out", "discard", "void",
               "cancel bill", "approve", "reject")


def _empty(err: str = "") -> dict:
    d = {k: [] for k in LIST_KEYS}
    d.update({"tables": [], "gridColumns": [], "gridScroll": [], "page": {}})
    if err:
        d["error"] = err
    return d


def _run_extract(page) -> dict:
    try:
        d = page.evaluate(EXTRACT_JS)
        return d if isinstance(d, dict) else _empty("extract ne dict nahi diya")
    except Exception as e:  # noqa: BLE001
        return _empty(str(e)[:200])


def _add_frames(page, data: dict):
    """iframe ke andar ke element bhi -- har ek par frame ka URL likha jata hai."""
    try:
        frames = list(page.frames)[1:6]
    except Exception:  # noqa: BLE001
        return
    for fr in frames:
        try:
            if not fr.url or fr.url == "about:blank":
                continue
            extra = fr.evaluate(EXTRACT_JS)
        except Exception:  # noqa: BLE001
            continue
        for k in LIST_KEYS:
            for el in (extra.get(k) or []):
                el["frame"] = fr.url
                data.setdefault(k, []).append(el)


def extract(bp: BasePage, ready_ms: int = 12000) -> dict:
    """
    Page ke saare element -- page taiyaar hone ke BAAD. Ek hi snapshot.

    12 second kaafi hai. Isse zyada wait karne ka matlab hai ki page load
    hi nahi ho raha -- us soorat me jo mila wo le lena behtar hai, kyunki
    50 page par 25-25 second bahut lamba ho jata hai.

    Pehle `ready` ka jawab phenk diya jata tha. Ab data me likha jata hai
    (ready / waited), taaki adhoora snapshot pehchana ja sake.
    """
    st = wait_ready(bp.page, timeout_ms=ready_ms)
    data = _run_extract(bp.page)
    data["ready"] = bool(st.get("ready"))
    data["waited"] = st.get("waited", 0)
    _add_frames(bp.page, data)
    return data


def count_elements(data: dict) -> int:
    return sum(len(data.get(k) or []) for k in LIST_KEYS)


# ---------------------------------------------------------------- collect

def _ekey(el: dict) -> tuple:
    """Ek element ki pehchan -- do snapshot me wahi element wahi key de."""
    return (el.get("elementType"),
            el.get("id") or el.get("formControlName") or el.get("name") or "",
            el.get("xpath") or el.get("cssSelector") or el.get("text") or "",
            el.get("frame", ""))


def merge_data(base: dict, new: dict, state: str = "") -> list[dict]:
    """
    Naya snapshot purane me jodo. Wapas: jo SACH MUCH naye mile.

    Jo pehle se hai use dobara nahi jodte. Par tab/accordion ka uid aur
    active/expanded ka haal naya wala le lete hain (Angular re-render kare to
    uid badal jata hai, aur purani uid par click nahi ho sakta).
    """
    added: list[dict] = []
    for k in LIST_KEYS:
        have = {_ekey(e): e for e in base.setdefault(k, [])}
        for e in (new.get(k) or []):
            key = _ekey(e)
            if key in have:
                if k in ("tabs", "collapsers", "customSelects"):
                    for f in ("uid", "active", "expanded"):
                        if f in e:
                            have[key][f] = e[f]
                continue
            if state:
                e = {**e, "state": state}
            base[k].append(e)
            have[key] = e
            added.append(e)

    # ag-Grid ke column -- id se
    cols = {c["id"]: c for c in base.setdefault("gridColumns", [])}
    for c in (new.get("gridColumns") or []):
        if c["id"] in cols:
            if c.get("label") and not cols[c["id"]].get("label"):
                cols[c["id"]]["label"] = c["label"]
            continue
        c = {**c, "state": state} if state else c
        base["gridColumns"].append(c)
        cols[c["id"]] = c
        added.append({"elementType": "gridColumn", **c})

    # grid scroll ka naap aur page ki jaankari taaza wali
    if new.get("gridScroll"):
        base["gridScroll"] = new["gridScroll"]
    if new.get("page") and not base.get("page"):
        base["page"] = new["page"]
    return added


def _label_of(el: dict) -> str:
    return (el.get("text") or el.get("ariaLabel") or el.get("title")
            or el.get("label") or "").strip()


def _safe_to_click(el: dict) -> tuple[bool, str]:
    """Tab/accordion dabana surakshit hai? (haan/nahi, wajah)"""
    if el.get("danger"):
        return False, "delete jaisa shabd"
    label = _label_of(el).lower()
    if any(w in label for w in STATE_BLOCK):
        return False, f"'{label[:24]}' dabana mana hai"
    href = (el.get("href") or "").strip()
    if href and not href.startswith(("#", "javascript")):
        return False, "ye doosre page par le jata hai (tab nahi, link hai)"
    if not el.get("uid"):
        return False, "pakki pehchan (uid) nahi"
    return True, ""


def _scroll_grid(page, data: dict, states: list, say=None):
    """
    ag-Grid ke saare column -- side me scroll karke padho.

    ag-Grid scroll se bahar ke column DOM me banata hi nahi, isliye ek
    snapshot me wo kabhi nahi aate. Sirf scroll hota hai, koi click nahi.
    """
    for g in (data.get("gridScroll") or [])[:4]:
        sw, cw = g.get("scrollWidth", 0), g.get("clientWidth", 0)
        if cw <= 0 or sw <= cw + 4:
            continue
        step = max(160, int(cw * 0.7))
        x, added = 0, 0
        for _ in range(60):
            x += step
            try:
                page.evaluate(GRID_SCROLL_JS, [g["index"], x])
                page.wait_for_timeout(220)
                cols = page.evaluate(GRID_COLS_JS) or []
            except Exception:  # noqa: BLE001
                break
            added += len(merge_data(data, {"gridColumns": cols},
                                    state=f"grid-scroll[{g['index']}]"))
            if x >= sw:
                break
        try:
            page.evaluate(GRID_SCROLL_JS, [g["index"], 0])      # jahan the wahin wapas
        except Exception:  # noqa: BLE001
            pass
        states.append({"state": f"grid[{g['index']}] side-scroll", "ok": True,
                       "added": added})
        if say and added:
            say(f"        (grid ke {added} aur column scroll karke mile)")


def explore_states(bp: BasePage, data: dict, states: list, max_states: int = 25,
                   say=None) -> int:
    """
    Har tab aur band accordion ek-ek karke kholo, aur har baar naye element jodo.

    Sirf wahi dabate hain jo surakshit hain (_safe_to_click). Jo koi dusre
    page par le jaye (href wala) use tab nahi maante.
    """
    from framework import net_wait, safety
    page = bp.page
    tried: set = set()
    total = 0
    for _ in range(max_states):
        cand = None
        for kind, key in (("tab", "tabs"), ("section", "collapsers")):
            for el in data.get(key) or []:
                k = (kind, _ekey(el))
                if k in tried:
                    continue
                if kind == "tab" and el.get("active"):
                    continue
                if kind == "section" and el.get("expanded"):
                    continue
                if el.get("inModal"):
                    continue
                cand = (kind, el, k)
                break
            if cand:
                break
        if not cand:
            break
        kind, el, k = cand
        tried.add(k)
        label = _label_of(el)[:28] or el.get("id") or "?"
        name = f"{kind}:{label}"
        ok, why = _safe_to_click(el)
        if not ok:
            states.append({"state": name, "ok": False, "why": why})
            continue
        try:
            loc = page.locator(f'[data-qa-uid="{el["uid"]}"]').first
            if not loc.count() or not loc.is_visible(timeout=800):
                states.append({"state": name, "ok": False, "why": "ab dikh nahi raha"})
                continue
            safety.guarded_click(loc, f"crawl.state:{label}", timeout=3000)
            page.wait_for_timeout(250)
            net_wait.wait_quiet(page, 300, 4000)
        except Exception as e:  # noqa: BLE001
            states.append({"state": name, "ok": False, "why": str(e)[:80]})
            continue
        added = merge_data(data, _run_extract(page), state=name)
        total += len(added)
        states.append({"state": name, "ok": True, "added": len(added)})
        if say and added:
            say(f"        ({name}: {len(added)} naye element)")
    return total


def explore_selects(bp: BasePage, data: dict, states: list, say=None,
                    max_trials: int = 20, budget_s: float = 40) -> int:
    """
    Dropdown badlo -- dekho kaunse naye field aate hain (conditional field).

    "Registered" chunne par GSTIN aata hai, "Composition" par kuch aur: aise
    field kisi ek snapshot me dikhte hi nahi.

    SIRF create form me, aur SIRF form ki haalat badalti hai. Kuch save nahi
    hota -- form bina save kiye band hota hai. Header/sidebar ke dropdown
    (company badalna jaise) aur popup ke andar ke dropdown nahi chhute.
    Har dropdown purane vikalp par wapas rakha jata hai.
    """
    from framework import net_wait
    page = bp.page
    t0 = time.time()
    trials = 0
    gained = 0
    conditional = data.setdefault("conditional", [])
    heading = ((data.get("page") or {}).get("heading") or "").lower()
    if "setting" in heading or "control room" in heading:
        return 0

    for d in list(data.get("dropdowns") or []):
        if trials >= max_trials or time.time() - t0 > budget_s:
            break
        css = d.get("cssSelector") or ""
        opts = [o.get("text", "") for o in (d.get("options") or [])]
        if not (css.startswith("select#") or css.startswith("select[")):
            continue
        if not (d.get("visible") and d.get("enabled")) or d.get("inModal") \
                or d.get("inChrome") or d.get("frame"):
            continue
        if not (2 <= len(opts) <= 8):
            continue
        cur = d.get("currentValue", "")
        what = d.get("label") or d.get("id") or d.get("formControlName") or css
        for opt in opts:
            if opt == cur or not opt or trials >= max_trials:
                continue
            trials += 1
            try:
                if not page.evaluate(SET_SELECT_JS, [css, opt]):
                    continue
                page.wait_for_timeout(250)
                net_wait.wait_quiet(page, 300, 4000)
            except Exception:  # noqa: BLE001
                break
            state = f"when:{what}={opt}"
            added = merge_data(data, _run_extract(page), state=state)
            ids = [a.get("id") or a.get("formControlName") or a.get("name")
                   or a.get("label") or a.get("text") for a in added]
            conditional.append({"when": f"{what} = {opt}", "select": css,
                                "newFields": [i for i in ids if i]})
            gained += len(added)
            states.append({"state": state, "ok": True, "added": len(added)})
            if say and added:
                say(f"        ({what} = {opt}: {len(added)} naye element)")
        try:                                   # purani value wapas
            page.evaluate(SET_SELECT_JS, [css, cur])
            page.wait_for_timeout(150)
        except Exception:  # noqa: BLE001
            pass
    return gained


def assess(data: dict) -> dict:
    """
    Ye snapshot bharosemand hai? -- 'ok' ya 'partial', aur wajah.

    Pehle koi bhi snapshot PASS ho jata tha: Sign In page ho, "not authorized"
    ho, ya sirf 2 element -- sab "PASS". Ab shak ho to saaf likha jata hai.
    """
    flags = []
    n = count_elements(data)
    hint = ((data.get("page") or {}).get("bodyHint") or "")
    if data.get("error"):
        flags.append("extract_error")
    if data.get("ready") is False:
        flags.append("not_ready")
    if n == 0:
        flags.append("empty")
    elif n < MIN_ELEMENTS:
        flags.append("few_elements")
    if any(w in hint for w in ("not authorized", "access denied", "unauthorized")):
        flags.append("not_authorized")
    if "sign in" in hint and "mobile / email" in hint:
        flags.append("login_page")
    return {"level": "ok" if not flags else "partial", "flags": flags,
            "elements": n}


def collect(bp: BasePage, ready_ms: int = 12000, deep: bool = False,
            explore: bool = True, say=None) -> dict:
    """
    Ek page ke saare element -- poori koshish ke saath.

      1. snapshot (extract)
      2. adhoora lage to thoda ruk kar dobara, aur jodo
      3. thodi der baad ek aur snapshot (der se bane field)
      4. ag-Grid ke saare column (side scroll)
      5. har tab aur band accordion kholna
      6. deep=True (sirf create form): dropdown badal kar conditional field

    Wapas wahi dict jo extract() deta hai, aur upar se:
      states      -- kya-kya khola, kitna naya mila, kahan atka
      conditional -- kaun sa dropdown badalne par kaunse field aaye
      quality     -- {"level": "ok"|"partial", "flags": [...]}
    """
    page = bp.page
    data = extract(bp, ready_ms)
    states: list = [{"state": "initial", "ok": True, "added": count_elements(data)}]

    # 2. adhoora? Ek baar aur -- par login/unauthorized page par nahi, wahan
    # dobara dekhne se kuch nahi badlega.
    for _ in range(2):
        q = assess(data)
        if q["level"] == "ok" or {"login_page", "not_authorized"} & set(q["flags"]):
            break
        wait_ready(page, timeout_ms=15000)
        page.wait_for_timeout(1200)
        again = extract(bp, 8000)
        added = merge_data(data, again, state="retry")
        data["ready"] = again.get("ready")
        states.append({"state": "retry", "ok": True, "added": len(added)})

    # 3. der se bane field
    page.wait_for_timeout(700)
    late = merge_data(data, _run_extract(page), state="late")
    if late:
        states.append({"state": "late", "ok": True, "added": len(late)})
        if say:
            say(f"        (der se {len(late)} element aur aaye)")

    # 4. grid ke column
    _scroll_grid(page, data, states, say)

    # 5/6. tab, accordion, dropdown
    if explore:
        explore_states(bp, data, states, say=say)
        if deep:
            explore_selects(bp, data, states, say=say)

    data["states"] = states
    data["quality"] = assess(data)
    return data


def collected_fields(data: dict) -> dict:
    """Row me jodne wale naye khaane."""
    return {k: data.get(k, []) for k in
            ("clickables", "customSelects", "tabs", "collapsers", "gridColumns",
             "states", "conditional")} | {
        "quality": data.get("quality", {}), "ready": data.get("ready")}


# ---------------------------------------------------------------- sidebar
#
# Crawl ki list pehle config/menu_sequence.json se aati thi -- haath se likhi
# hui, 49 page. Source me 375 route hain. Banking aur CRM me kuch likha hi
# nahi tha, Staff Register gayab tha, aur Report/Utilities ke andar ke page
# kabhi nahi khule.
#
# Ab sidebar ko KHUD padhte hain. MargBooks ka sidebar ek nested <ul><li> tree
# hai (Layout/menu.component.html) aur band (collapsed) items bhi DOM me
# pehle se maujood rehte hain -- isliye bina ek bhi click ke poora tree mil
# jata hai:
#   top group  : <a class="dropdown-toggle" id="menu<value>">  + <ul.collapse>
#   top leaf   : <a class="menulink" id="menu-<i>-<value>">
#   nested grp : <a class="dropdown-toggle" href="#menu-..">   (id NAHI hota)
#                + <menu><ul>...</ul></menu>
#   nested leaf: <a id="menu-<i>-<j>-<value>">
#   "+"        : <a class="addLInks"> -- leaf ke bagal me
SIDEBAR_JS = r"""
() => {
  const norm = t => (t || '').replace(/\s+/g, ' ').trim();
  const root = document.querySelector('ul#ul_id')
            || (document.querySelector('li.grandParent') || {}).parentElement;
  if (!root) return null;

  const label = a => norm((a.querySelector('span') || a).innerText
                          || a.getAttribute('title') || a.textContent);
  const selOf = a => a.id ? `[id="${a.id}"]`
                   : (a.getAttribute('href') ? `a[href="${a.getAttribute('href')}"]` : '');

  const walk = (ul) => {
    const out = [];
    for (const li of ul.children) {
      if (li.tagName !== 'LI') continue;
      const anchors = [...li.children].filter(e => e.tagName === 'A');
      const main = anchors.find(a => !a.classList.contains('addLInks'));
      if (!main) continue;
      const plus = anchors.find(a => a.classList.contains('addLInks'));
      const sub = li.querySelector(':scope > ul, :scope > menu > ul');
      const sel = selOf(main);
      const id = main.id || '';
      out.push({
        name: label(main),
        id, sel,
        value: id ? id.split('-').pop().replace(/^menu/, '') : '',
        kind: main.classList.contains('dropdown-toggle') ? 'group' : 'leaf',
        create: !!plus,
        plusSel: plus && sel ? `${sel} + a.addLInks` : '',
        hidden: !!(li.hidden || main.hidden),
        disabled: main.classList.contains('disabledmenu'),
        fav: /-fav-/.test(id) || /fav-/.test(main.getAttribute('href') || ''),
        children: sub ? walk(sub) : [],
      });
    }
    return out;
  };
  return walk(root);
}
"""

# In menu ke list-page par "Create" ka button hota hai (masters, accounting,
# stock). Sale/Purchase ke list par bhi, par wahan sirf wahi try karte hain
# jinke saamne "+" hai -- baaki (Draft, POS...) sirf list hain.
CREATE_FAMILIES = {"master", "accounting trans.", "stock management",
                   "banking", "crm"}


def discover_sidebar(page, wait_s: float = 15) -> list[dict] | None:
    """Sidebar ka poora tree -- ya None agar sidebar mila hi nahi."""
    deadline = time.time() + wait_s
    while True:
        try:
            tree = page.evaluate(SIDEBAR_JS)
        except Exception:  # noqa: BLE001
            tree = None
        if tree:
            return tree
        if time.time() >= deadline:
            return None
        page.wait_for_timeout(500)


def _nm(s) -> str:
    return " ".join(str(s or "").lower().split())


def _config_index(config: dict) -> dict:
    """menu_sequence.json ko (naam ka rasta) -> entry me badlo."""
    idx: dict[tuple, dict] = {}

    def walk(nodes, trail):
        for n in nodes or []:
            p = trail + (_nm(n.get("name")),)
            idx[p] = n
            walk(n.get("children"), p)

    for m in (config or {}).get("menus", []):
        top = (_nm(m.get("name")),)
        idx[top] = m
        walk(m.get("submenus"), top)
    return idx


def build_sequence(tree: list[dict], config: dict | None = None) -> dict:
    """
    Live sidebar + haath ki config = crawl ki list.

    Sidebar SACH batata hai ki kya hai. Config sirf jaankari jodti hai jo
    sidebar nahi de sakta: kaunsa menu chhodna hai (aur kyun), form ka
    doosra naam, aur screens.py wala naam. Config me jo menu sidebar me mila
    hi nahi, use bhi list me rakhte hain -- chupchaap girana mana hai, wo
    "nahi mila" ke haal ke saath dikhega.
    """
    idx = _config_index(config or {})

    def conv(n, trail, top_name, order):
        p = trail + (_nm(n["name"]),)
        cfg = idx.get(p, {})
        out = {"order": order, "name": n["name"], "id": n.get("id", ""),
               "sel": n.get("sel", ""), "value": n.get("value", "")}
        for k in ("screen", "formNames", "skip", "skip_reason"):
            if k in cfg:
                out[k] = cfg[k]
        if (n.get("hidden") or n.get("disabled")) and not cfg.get("skip"):
            out["skip"] = True
            out["skip_reason"] = ("sidebar me chhupa/band hai -- ye is company "
                                  "ya plan me nahi hai")
        kids = [conv(c, p, top_name, i) for i, c in
                enumerate([c for c in n.get("children", []) if not c.get("fav")], 1)]
        if kids:
            out["children"] = kids
            return out
        # patta (leaf)
        if n.get("kind") == "group":
            out["emptyGroup"] = True          # khula to, par andar kuch nahi
            out["create"] = False
        elif "create" in cfg:
            out["create"] = bool(cfg["create"])
        else:
            out["create"] = bool(n.get("create")) or _nm(top_name) in CREATE_FAMILIES
        if n.get("plusSel"):
            out["plusSel"] = n["plusSel"]
        return out

    menus = []
    seen = set()
    live = [n for n in tree if not n.get("fav")]
    for i, n in enumerate(live, 1):
        t = conv(n, (), n["name"], i)
        seen.add(_nm(n["name"]))
        top = {"order": i, "name": t["name"], "id": t["id"], "sel": t["sel"]}
        for k in ("skip", "skip_reason"):
            if k in t:
                top[k] = t[k]
        if t.get("children"):
            top["submenus"] = t["children"]
        else:
            top["leaf"] = True
        menus.append(top)

    # Config me hai par sidebar me nahi mila -- dikhta rahe
    extra = 0
    for m in (config or {}).get("menus", []):
        if _nm(m.get("name")) not in seen:
            extra += 1
            menus.append({**m, "order": len(live) + extra, "notInSidebar": True})
    return {"menus": menus, "control_room": (config or {}).get("control_room", {})}


def count_pages(seq: dict) -> int:
    """Kitne page (patte) visit hone hain."""
    def leaves(nodes):
        n = 0
        for x in nodes or []:
            kids = x.get("children") or []
            n += leaves(kids) if kids else 1
        return n
    total = 0
    for m in seq.get("menus", []):
        subs = m.get("submenus") or []
        total += leaves(subs) if subs else (1 if m.get("leaf") else 0)
    return total


# ---------------------------------------------------------------- crawler

class Crawler:
    def __init__(self, bp: BasePage, resume: bool = False,
                 retry: int = 2, verbose: bool = True,
                 enable: str = "none", budget_min: int = 90,
                 discover: bool = True):
        self.bp = bp
        # True = menu ki list live sidebar se banegi (config sirf jaankari
        # jodti hai). False = purani tarah sirf config/menu_sequence.json.
        self.discover = discover
        self.page = bp.page
        self.retry = retry
        self.verbose = verbose
        # "none"   -- kuch nahi badalna (default)
        # "all"    -- HAR wo setting jiske dropdown me "Yes" ka vikalp hai
        # "known"  -- sirf 15 jaani-pehchani settings (chhota sweep)
        #
        # Pehle "--enable" ka matlab "known" tha. Us par sirf 2-3 settings
        # badalti thin, kyunki baaki pehle se Yes thin -- aur chhupe hue
        # field phir bhi nahi dikhte the. Ab "--enable" ka matlab SAARI hai.
        self.enable = enable
        # Poore crawl ki seema. Ek crawl 28 ghante chal chuka hai aur sirf
        # 3 page nikale -- kyunki app mar chuki thi aur crawler koshish
        # karta raha. Seema hone se aisa dobara nahi hoga.
        self.budget_s = budget_min * 60
        self.seq = json.loads(SEQ_FILE.read_text(encoding="utf-8"))
        self.seq_config = self.seq          # haath ki config -- discovery iske upar
        self._trail: list[dict] = []        # abhi kaunse menu khule hone chahiye
        self.sidebar_info: dict = {}
        self.state = self._load_state() if resume else {"done": []}
        self.pages: list[dict] = []
        self.menus: list[dict] = []
        self.control_room: dict = {}
        self.status: list[dict] = []
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "screenshots").mkdir(exist_ok=True)
        (OUT / "raw").mkdir(exist_ok=True)
        (OUT / "logs").mkdir(exist_ok=True)

    # ---- chhoti madad ----

    def say(self, msg: str):
        if self.verbose:
            print(msg)
        logbook.write("scanner", "crawl", "info", note=msg[:200])

    def _load_state(self) -> dict:
        f = OUT / "state.json"
        if not f.exists():
            return {"done": []}
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {"done": []}

    def _save_state(self):
        (OUT / "state.json").write_text(
            json.dumps(self.state, indent=1), encoding="utf-8")

    def _mark(self, kind: str, name: str, status: str, **extra):
        """Har cheez ka ek haal. Chupchaap chhodna mana hai."""
        self.status.append({"type": kind, "name": name, "status": status,
                            **extra})

    def _key(self, *parts) -> str:
        return " > ".join(str(p) for p in parts if p)

    # ---- app zinda hai ya nahi ----
    #
    # ASLI GHATNA: crawl 28.7 GHANTE chala aur sirf 3 page nikale.
    # 'Group > CREATE' ke theek baad app ka session khatam ho gaya -- saare
    # menu gayab, Settings ka icon bhi gayab. Crawler ne use "menu nahi
    # mila" samjha aur AGE badhta raha: har menu par retry, har retry par
    # 12-20 second ka wait. Aise 8 menu, phir 5 page, phir Control Room.
    #
    # Ek mari hui app par ghanton koshish karna bekaar hai. Ek baar dekh
    # lena chahiye ki app zinda hai bhi ya nahi -- aur nahi hai to ya wapas
    # laao, ya SAAF ruk jao.

    def _app_alive(self) -> bool:
        """Sidebar ke menu abhi maujood hain?"""
        try:
            n = self.page.evaluate(
                "() => document.querySelectorAll('a.menulink, #nav a, "
                "a.dropdown-toggle').length")
            return bool(n and n > 3)
        except Exception:  # noqa: BLE001
            return False

    def _revive(self) -> bool:
        """
        App wapas laane ki koshish -- do kadam, phir haar maan lo.

        1. dashboard par jao (SPA atak gaya ho to isse theek ho jata hai)
        2. dobara login (session khatam ho gaya ho)

        Dono fail ho to aage badhna bekaar hai.
        """
        self.say("      (app se koi jawab nahi -- wapas laane ki koshish)")
        try:
            self.bp.goto("/dashboard")
            wait_ready(self.page, timeout_ms=15000)
            if self._app_alive():
                self.say("      (app wapas aa gaya)")
                return True
        except Exception:  # noqa: BLE001
            pass

        try:
            from framework.auth import login
            self.say("      (dobara login kar rahe hain)")
            self.bp = login(self.page, verbose=False)
            self.page = self.bp.page
            wait_ready(self.page, timeout_ms=20000)
            if self._app_alive():
                self.say("      (login ke baad app wapas aa gaya)")
                return True
        except Exception as e:  # noqa: BLE001
            self.say(f"      (login bhi nahi hua: {str(e)[:70]})")
        return False

    def _home(self):
        """Har menu se pehle ek jaani-pehchani haalat par aao."""
        safety.dismiss_modal(self.page)
        safety.force_close_modal(self.page)
        try:
            self.bp.goto("/dashboard")
            wait_ready(self.page, timeout_ms=10000)
        except Exception:  # noqa: BLE001
            pass
        # Sign In page aa gaya? Matlab session gaya -- chupchaap aage mat badho,
        # ek baar saaf bol ke wapas lao. (Pehle yahi cheez "app mar gayi"
        # samjhi gayi aur ghanton ka chakkar chala.)
        if self._on_login_page():
            self.say("      (Sign In page aa gaya -- session gaya, wapas login)")
            self._revive()

    def _on_login_page(self) -> bool:
        """Abhi Sign In screen par hain? (sidebar nahi, login ka box hai)"""
        try:
            return bool(self.page.evaluate(
                "() => !!document.querySelector('input#userid, input[name=\"username\"]')"
                " && !document.querySelector('a.menulink, #ul_id')"))
        except Exception:  # noqa: BLE001
            return False

    # ---- menu kholna: toggle nahi, STHITI dekh kar ----
    #
    # Sidebar ke group click par KHULTE-BAND hote hain (toggle). Khule hue par
    # dobara click karne se wo band ho jata hai -- screens_check me yahi galti
    # pehle pakdi ja chuki hai ("ek chhodkar ek screen fail"). Isliye click se
    # pehle dekho ki wo pehle se khula to nahi.

    def _expanded(self, sel: str):
        """Group khula hai? True/False, ya None agar mila hi nahi."""
        if not sel:
            return None
        try:
            return self.page.evaluate(
                """(s) => { const e = document.querySelector(s);
                            if (!e) return null;
                            const a = e.getAttribute('aria-expanded');
                            if (a === 'true') return true;
                            if (a === 'false') return false;
                            return !e.classList.contains('collapsed'); }""", sel)
        except Exception:  # noqa: BLE001
            return None

    def _sel_visible(self, sel: str) -> bool:
        if not sel:
            return False
        try:
            return bool(self.page.evaluate(
                """(s) => { const e = document.querySelector(s);
                            if (!e) return false;
                            const r = e.getBoundingClientRect();
                            return r.width > 0 && r.height > 0; }""", sel))
        except Exception:  # noqa: BLE001
            return False

    def _ensure_open(self, node: dict) -> bool:
        """Is group ko KHULA karo (khula ho to chhedo mat)."""
        sel = node.get("sel") or (f'[id="{node["id"]}"]' if node.get("id") else "")
        if self._expanded(sel) is True:
            return True
        if not self._click_text(node.get("name", ""), el_id=node.get("id", ""),
                                sel=node.get("sel", "")):
            return False
        self.page.wait_for_timeout(700)
        st = self._expanded(sel)
        return True if st is None else bool(st)

    def _open_trail(self, trail: list[dict]) -> bool:
        """Upar se neeche ek-ek group kholo."""
        for g in trail:
            if not self._ensure_open(g):
                return False
        return True

    def _reopen(self, menu: str = "", sub: str = "") -> bool:
        """Ghar jao aur wahi menu dobara kholo jahan the."""
        self._home()
        trail = getattr(self, "_trail", None)
        if trail:
            return self._open_trail(trail)
        if menu:
            self._click_text(menu)
        if sub:
            self._click_text(sub)
        return True

    def _shot(self, name: str):
        try:
            safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in name)
            self.page.screenshot(path=str(OUT / "screenshots" / f"{safe}.png"))
        except Exception:  # noqa: BLE001
            pass

    # ---- menu ----

    def _menu_identity(self, name: str, mid: str = "") -> dict | None:
        """Menu ko sirf text se nahi -- id, class, XPath sab se pehchano."""
        try:
            return self.page.evaluate(r"""
              ([name, mid]) => {
                const norm = t => (t || '').replace(/\s+/g,' ').trim();
                const all = [...document.querySelectorAll('a, [role=menuitem], button')];
                let el = mid ? document.getElementById(mid) : null;
                if (!el) el = all.find(e => norm(e.innerText) === name);
                if (!el) el = all.find(e => norm(e.innerText).startsWith(name));
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return {
                  name, text: norm(el.innerText), id: el.id || '',
                  class: (typeof el.className === 'string' ? el.className : ''),
                  role: el.getAttribute('role') || '',
                  cssSelector: el.id ? `#${el.id}`
                    : `a:has-text("${norm(el.innerText)}")`,
                  xpath: el.id ? `//*[@id="${el.id}"]`
                    : `//a[normalize-space(text())="${norm(el.innerText)}"]`,
                  visible: r.width > 0 && r.height > 0,
                };
              }
            """, [name, mid])
        except Exception:  # noqa: BLE001
            return None

    def _click_text(self, name: str, timeout: int = 6000,
                    el_id: str = "", sel: str = "") -> bool:
        """
        Menu/submenu par click.

        ID PEHLE -- text baad me.
        ================================
        ASLI BUG: crawler menu ka id dhoondh leta tha (#menu495210260 =
        Master), aur phir use PHENK kar TEXT se click karta tha. Text se
        click isliye fail hua ki "Sale" aur "Purchase" DO-DO jagah hain --
        top menu me bhi, aur Master > Accounts Master ke andar bhi.
        Playwright ko do element mile aur wo galat wale par atak gaya.

        Saboot: Dashboard, Report aur Utilities & Tools chal gaye -- unke
        naam kahin dobara nahi aate. Master, Sale, Purchase, Accounting,
        Stock, Banking, CRM -- saat ke saat fail, aur saaton ke naam kahin
        na kahin dobara aate hain.

        Id already mil chuki hai. Use na use karna sirf apna nuksaan tha.
        """
        finders = []
        if sel:
            # Sidebar se mila pakka selector (nested group me id hoti hi nahi,
            # sirf href hota hai).
            finders.append(lambda: self.page.locator(sel).first)
        if el_id:
            finders.append(lambda: self.page.locator(f'[id="{el_id}"]').first)
        finders += [
            # Sidebar ke andar hi dhoondho -- content area me wahi naam
            # dobara ho sakta hai
            lambda: self.page.locator("#nav, .sidebar, nav")
                        .get_by_text(name, exact=True).first,
            lambda: self.page.get_by_role("link", name=name, exact=True).first,
            lambda: self.page.get_by_text(name, exact=True).first,
        ]

        for finder in finders:
            try:
                el = finder()
                if el.count() == 0:
                    continue
                if not el.is_visible(timeout=1500):
                    continue
                safety.guarded_click(el, f"crawl:{name}", timeout=timeout)
                wait_ready(self.page, timeout_ms=12000)
                return True
            except Exception:  # noqa: BLE001
                continue
        return False

    def _submenus_on_screen(self, expected: list[str]) -> list[dict]:
        """Menu khulne par uske andar kya-kya dikh raha hai."""
        try:
            found = self.page.evaluate(r"""
              () => [...document.querySelectorAll('a.menulink, a.dropdown-toggle')]
                .filter(e => { const r = e.getBoundingClientRect();
                               return r.width > 0 && r.height > 0; })
                .map(e => ({text: (e.innerText||'').replace(/\s+/g,' ').trim(),
                            id: e.id || ''}))
                .filter(x => x.text)
            """) or []
        except Exception:  # noqa: BLE001
            found = []
        names = {f["text"] for f in found}
        return [{"name": n, "onScreen": n in names} for n in expected]

    # ---- ek page ----

    def _on_screen(self, label: str) -> bool:
        """Ye cheez abhi screen par dikh bhi rahi hai?"""
        try:
            return bool(self.page.evaluate(r"""
              (name) => [...document.querySelectorAll('a, button, [role=menuitem]')]
                .some(e => {
                  const t = (e.innerText || '').replace(/\s+/g,' ').trim();
                  const r = e.getBoundingClientRect();
                  return r.width > 0 && r.height > 0 &&
                         (t === name || t.startsWith(name));
                })
            """, label))
        except Exception:  # noqa: BLE001
            return False

    def _do_page(self, menu: str, sub: str, child: str = "",
                 node: dict | None = None) -> dict:
        """
        node = sidebar se mila item (id / pakka selector ke saath). Diya ho
        to click usi se hota hai -- text se nahi. "Bill", "Order", "Return"
        Sale aur Purchase dono me hain; text se galat wale par jaa sakte hain.
        """
        key = self._key(menu, sub, child)
        label = child or sub
        node = node or {}

        # App zinda hai? Ek menu ke andar 12 submenu ho sakte hain; mari
        # hui app par har ek apna wait poora karega.
        if not self._app_alive():
            self._mark("page", key, BLOCKED,
                       reason="app se koi jawab nahi tha")
            self.say(f"      [BLOCKED] {label} -- app se koi jawab nahi")
            return {"status": BLOCKED}

        # Screen par hai hi nahi -> koshish hi mat karo.
        #
        # Pehle ye do baar retry karta tha, har baar 18-25 second wait ke
        # saath. Asli app me 37 submenu hain -- teen-char gayab hue to crawl
        # ghanton ka ho jata. Aur retry se kuch milta bhi nahi: jo cheez
        # screen par nahi hai, wo dobara dekhne se aa nahi jayegi.
        shown = (self._sel_visible(node["sel"]) if node.get("sel")
                 else self._on_screen(label))
        if not shown:
            self._mark("page", key, BLOCKED,
                       reason="ye item menu me dikha hi nahi "
                              "(permission nahi, ya is company me hai hi nahi)")
            self.say(f"      [BLOCKED] {label} -- menu me dikha hi nahi")
            return {"status": BLOCKED}

        for attempt in range(1, self.retry + 2):
            try:
                lid = node.get("id") or (self._menu_identity(label) or {}).get("id", "")
                if not self._click_text(label, el_id=lid, sel=node.get("sel", "")):
                    if attempt <= self.retry:
                        self._reopen(menu, sub if sub != label else "")
                        continue
                    self._mark("page", key, FAILED, reason="submenu nahi mila")
                    self._shot(f"fail-{key}")
                    self.say(f"      [FAIL] '{label}' nahi mila")
                    return {"status": FAILED}

                data = collect(self.bp, say=self.say)
                n = count_elements(data)
                q = data.get("quality") or {}
                st = PASS if q.get("level") == "ok" else PARTIAL
                row = {
                    "id": key.replace(" > ", "/"),
                    "menu": menu, "submenu": sub, "child": child,
                    "name": label,
                    "url": (data.get("page") or {}).get("url", ""),
                    "title": (data.get("page") or {}).get("title", ""),
                    "heading": (data.get("page") or {}).get("heading", ""),
                    "elements": n,
                    "inputs": data.get("inputs", []),
                    "buttons": data.get("buttons", []),
                    "dropdowns": data.get("dropdowns", []),
                    "checkboxes": data.get("checkboxes", []),
                    "links": (data.get("links") or [])[:400],
                    "tables": data.get("tables", []),
                    **collected_fields(data),
                    "status": st,
                }
                self.pages.append(row)
                self._save_page(row)          # HAR page ke baad turant
                self._mark("page", key, st, elements=n, flags=q.get("flags"))
                if st == PASS:
                    self.say(f"      [PASS] {label}  -- {n} element")
                else:
                    self.say(f"      [PARTIAL] {label}  -- {n} element, shak: "
                             f"{', '.join(q.get('flags') or [])}")
                return row

            except Exception as e:  # noqa: BLE001
                if attempt <= self.retry:
                    self.say(f"      koshish {attempt} fail, dobara: {str(e)[:70]}")
                    self._reopen(menu)
                    continue
                self._mark("page", key, FAILED, reason=str(e)[:200])
                self._shot(f"fail-{key}")
                self.say(f"      [FAIL] {label} -- {str(e)[:90]}")
                return {"status": FAILED}
        return {"status": FAILED}

    # ---- create form ----
    #
    # Asli kaam create form me hota hai -- list me sirf padha jata hai.
    # List ke element se koi test nahi bante; jo bante hain wo form ke
    # field se bante hain. Isliye har jagah jahan create ho sakta hai,
    # form khol kar uska poora naksha lete hain.
    #
    # Do raaste hain, aur dono lagte hain:
    #   masters       -> list page par "Create/F2" ka button
    #   transactions  -> submenu ke SAAMNE "+" ka icon
    # Isliye dono try karte hain, jo bhi mile.

    # "+ Create Receipt Voucher List" jaise poore naam bhi hote hain,
    # isliye "+ Create" aur "Create" dono se dhoondhte hain (exact=False).
    CREATE_LABELS = ("Create/F2", "+ Create", "Create", "Add New", "New")

    # In par KABHI click nahi karna. Crawler padhta hai, likhta nahi.
    NEVER_CLICK = ("save", "f10", "submit", "post", "confirm", "delete",
                   "remove", "print")

    def _open_create(self, menu: str, sub: str, plus_sel: str = "") -> bool:
        """
        Create form kholo.

        KRAM: pehle list ka "Create" button, phir submenu ka "+".

        Ye kram jaan-boojh kar hai. Create button USI list page par hota
        hai jo abhi khuli hai -- wo galat module ka ho hi nahi sakta.
        "+" sidebar me hota hai, jahan aas-paas doosre module ke "+" bhi
        hote hain. Group ka create maang kar Ledger ka form khul chuka
        hai isi wajah se.

        Jahan "+" nahi hai (jaise Group), wahan ab Create button se kaam
        ho jayega -- yahi hona bhi chahiye.
        """
        # 1. list page par Create/F2 -- ye hamesha isi list ka hota hai
        for label in self.CREATE_LABELS:
            try:
                btn = self.page.get_by_role("button", name=label,
                                            exact=False).first
                if btn.count() and btn.is_visible(timeout=1200):
                    safety.guarded_click(btn, f"crawl.create:{sub}", timeout=6000)
                    wait_ready(self.page, timeout_ms=15000)
                    self._clear_create_popups()
                    return True
            except Exception:  # noqa: BLE001
                continue

        # 2a. sidebar se mila PAKKA "+" (isi item ke bagal wala, adjacent
        #     selector se) -- naam se dhoondhne wale se zyada bharosemand.
        if plus_sel and self._sel_visible(plus_sel):
            try:
                safety.guarded_click(self.page.locator(plus_sel).first,
                                     f"crawl.plus:{sub}", timeout=6000)
                wait_ready(self.page, timeout_ms=15000)
                self._clear_create_popups()
                return True
            except Exception:  # noqa: BLE001
                pass

        # 2. sidebar me submenu ke saamne wala "+"
        try:
            from framework import nav
            if nav.click_submenu_plus(self.bp, sub):
                wait_ready(self.page, timeout_ms=15000)
                self._clear_create_popups()
                return True
        except Exception:  # noqa: BLE001
            pass

        return False

    def _panel_heading(self) -> str:
        try:
            return self.page.evaluate(
                "() => { const h = document.querySelector("
                "'h1, h2, .mhead, .modal-title');"
                "  return h ? (h.innerText||'').trim() : ''; }") or ""
        except Exception:  # noqa: BLE001
            return ""

    def _form_present(self) -> bool:
        """Form abhi khula hai? (band karte waqt ye jaanch zaroori hai)"""
        try:
            return bool(self.page.evaluate("""() => !!(
                document.querySelector('[id^="txtLedgerName"]') ||
                document.querySelector('[id^="txtentryNo"]') ||
                document.querySelector('[id^="btnSave"]'))"""))
        except Exception:  # noqa: BLE001
            return False

    def _close_settings_panel(self, wait_s: float = 6) -> bool:
        """
        Form ke upar chipke hue Settings panel ko hatao.

        DO BAATEIN JO PICHHLI BAAR CHHOOT GAYIN
        =======================================
        1. Panel DER SE aata hai. Pehli koshish me maine turant dekha aur
           "panel nahi hai" maan liya -- par wo ek-do second baad bana, aur
           extract ne use pakad liya. Wahi galti Purchase popup ke saath bhi
           hui thi. Isliye ab thodi der INTEZAAR karte hain.

        2. "#btnClose" ka text "Esc Close" hai -- bilkul form ke btnEsc56
           jaisa. Wo panel ka nahi, FORM ka close bhi ho sakta hai. Isliye
           har click ke BAAD jaanchte hain ki form abhi bhi khula hai. Form
           chala gaya to jo mehnat form kholne me lagi wo bekaar.

        DHYAAN: "Apply" KABHI nahi dabate -- wo settings SAVE kar deta hai.
        """
        import time as _t

        # panel dikhne ka intezaar
        deadline = _t.time() + wait_s
        while _t.time() < deadline:
            if "setting" in self._panel_heading().lower():
                break
            self.page.wait_for_timeout(400)
        else:
            return False

        # Panel band karne wale button, ASLI PEHLE.
        #
        # ".itemcontrolClose" hi asli hai -- MargBooks ke settings panel ka
        # apna "x". Ye saboot dump me pehle se tha:
        #     <h2 class="headingItem">Sale Bill Setting x</h2>
        #     <button class="close itemcontrolClose">x</button>
        # Par maine metadata me "close" jaise BUTTON dhoondhe aur ye chhoot
        # gaya. Isi wajah se Sale ke SAATON form block hue -- form khule
        # the, panel bhi khula tha, aur maine mila-jula data lene se mana
        # kar diya.
        #
        # btnEsc* JAAN-BOOJH KAR nahi hai -- wo poora form band kar deta hai.
        sels = (".itemcontrolClose", ".headingItem .close",
                'button[id^="close-"]', "#btnClose", "#btn-Close",
                "button.btn-close", '[aria-label="Close"]')

        for attempt in range(3):
            head = self._panel_heading()
            if "setting" not in head.lower():
                return True                      # panel ja chuka

            closed = False
            for sel in sels:
                try:
                    b = self.page.locator(sel).first
                    if not b.count() or not b.is_visible(timeout=700):
                        continue
                    safety.guarded_click(b, "crawl.close-settings",
                                         inside_modal=True, timeout=5000)
                    self.page.wait_for_timeout(700)

                    if not self._form_present():
                        # Form hi band ho gaya -- ye button panel ka nahi tha
                        self.say(f"        (!! '{sel}' ne FORM band kar diya)")
                        return False
                    closed = True
                    break
                except Exception:  # noqa: BLE001
                    continue

            if not closed:
                self.page.wait_for_timeout(600)

        gone = "setting" not in self._panel_heading().lower()
        if gone:
            self.say("        (Settings panel band kiya)")
        else:
            self.say(f"        (!! Settings panel band nahi hua: "
                     f"{self._panel_heading()[:34]!r})")
        return gone

    def _clear_create_popups(self):
        """
        Form khulte hi jo popup aate hain, unhe raste se hatao.

        Purchase Bill par ek popup aata hai: "How would you like to create
        your purchase bill" -- Upload karein ya Manual. Iske bina form
        aata hi nahi.

        PEHLE POPUP KE AANE KA INTEZAAR, PHIR BUTTON DHOONDHNA.
        =======================================================
        Pichhli baar main turant button dhoondhta tha. Popup 1-2 second
        baad banta hai, isliye us waqt wo tha hi nahi -- count() 0 aaya
        aur main aage badh gaya. Metadata me wo button DOM me DIKHA par
        visible=False, jo yahi baat batata hai.

        Ab pehle popup ke aane tak rukte hain (6 second tak), phir uske
        andar ka button dabate hain.
        """
        labels = ("Start Manual Entry", "Manual Entry", "Create Manually",
                  "Enter Manually", "Continue", "Skip")
        # role=button se na mile to seedha text se. Kabhi button ka
        # accessible naam alag hota hai (icon, span, extra whitespace).
        css_fallbacks = ('button:has-text("Manual Entry")',
                         'button:has-text("Start Manual")',
                         '.outline-btn')

        # 1. Popup aaya ya nahi -- iska intezaar.
        # 6 second kam pada tha (Purchase ke saaton form chhoot gaye),
        # isliye 12.
        deadline = time.time() + 12
        found = None
        while time.time() < deadline and not found:
            for label in labels:
                try:
                    b = self.page.get_by_role("button", name=label,
                                              exact=False).first
                    if not b.count():
                        b = self.page.get_by_text(label, exact=False).first
                    if b.count() and b.is_visible():
                        found = (label, b)
                        break
                except Exception:  # noqa: BLE001
                    continue
            if not found:
                for css in css_fallbacks:
                    try:
                        b = self.page.locator(css).first
                        if b.count() and b.is_visible():
                            found = (css, b)
                            break
                    except Exception:  # noqa: BLE001
                        continue
            if not found:
                self.page.wait_for_timeout(300)

        # 2. Mil gaya to dabao -- popup ke ANDAR se, isliye inside_modal
        if found:
            label, b = found
            try:
                safety.guarded_click(b, f"crawl.popup:{label}",
                                     inside_modal=True, timeout=6000)
                wait_ready(self.page, timeout_ms=15000)
                self.say(f"        (popup: '{label}' daba diya)")
                return
            except Exception:  # noqa: BLE001
                pass

        safety.dismiss_modal(self.page)

    def _close_create(self):
        """
        Form BINA SAVE KIYE band karo.

        Ye crawler ka sabse nazuk hissa hai: yahan ek galat click asli
        data bana dega. Isliye sirf Esc/Close dabate hain, aur "data will
        be lost" wali confirmation par Yes -- jo data MITATA nahi, banne
        se rokta hai.
        """
        for sel in ('button[id^="btnEsc"]', "#btn-Close", "button.btn-close"):
            try:
                b = self.page.locator(sel).first
                if b.count() and b.is_visible(timeout=1200):
                    safety.guarded_click(b, "crawl.close", timeout=5000)
                    self.page.wait_for_timeout(700)
                    break
            except Exception:  # noqa: BLE001
                continue

        # "Transaction data will be loss, Are you sure?" -> Yes
        # Ye bill BANNE se rokta hai. Isliye yahan Yes hi sahi hai.
        for sel in ("#btnYes", 'button:has-text("Yes")'):
            try:
                b = self.page.locator(sel).first
                if b.count() and b.is_visible(timeout=1000):
                    safety.guarded_click(b, "crawl.discard", timeout=4000)
                    self.page.wait_for_timeout(600)
                    break
            except Exception:  # noqa: BLE001
                continue
        safety.force_close_modal(self.page)

    def _form_matches(self, label: str, aliases=None) -> tuple[bool, str]:
        """
        Jo form khula, wo ISI cheez ka hai?

        Ye doosri rok hai. Pehli rok nav.py me hai ("+" apni row se bahar
        na jaye). Par ek rok kabhi kaafi nahi hoti -- agar wo kabhi chhoot
        gayi to yahan pakda jayega.

        Galat form ka data "Group ka create form" naam se save ho jana
        sabse bura natija hai: wo galat lagta bhi nahi, aur uspe bane test
        hamesha galat cheez jaanchte rahenge.
        """
        try:
            head = self.page.evaluate(
                "() => { const h = document.querySelector("
                "'h1, h2, .mhead, .modal-title, .pageTitle');"
                "  return h ? (h.innerText||'').trim() : ''; }") or ""
        except Exception:  # noqa: BLE001
            return True, ""            # padh nahi paye to rok nahi lagate

        if not head:
            return True, ""

        def words(t):
            return {w for w in "".join(
                c if c.isalnum() else " " for c in t.lower()).split()
                if len(w) > 2 and w not in ("create", "new", "add", "master",
                                            "form", "entry")}

        got = words(head)
        if not got:
            return True, head

        # Menu ka naam, aur uske doosre naam bhi.
        #
        # MargBooks kuch cheezon ko form me ALAG naam se bulata hai:
        # "Ledger" ka form "Create Party" hai, "Agency" ka "Create Company".
        # Iske bina crawler samajhta hai ki galat form khul gaya, aur sahi
        # data chhod deta hai -- jo pichhle crawl me 4 form ke saath hua.
        names = [label] + list(aliases or [])
        for n in names:
            want = words(n)
            if want and (want & got):
                return True, head
        return False, head

    def _field_ids(self) -> set:
        """Abhi page par kaunse field hain -- unki pehchan."""
        try:
            return set(self.page.evaluate(r"""
              () => [...document.querySelectorAll('input, select, textarea')]
                .filter(e => { const r = e.getBoundingClientRect();
                               return r.width > 0 && r.height > 0
                                      && e.type !== 'hidden'; })
                .map(e => e.id || e.getAttribute('formcontrolname')
                          || e.getAttribute('name') || '')
                .filter(Boolean)
            """) or [])
        except Exception:  # noqa: BLE001
            return set()

    def _do_create(self, menu: str, sub: str, child: str = "",
                   before: set | None = None,
                   aliases: list | None = None,
                   node: dict | None = None) -> dict | None:
        label = child or sub
        key = self._key(menu, sub, child) + " > CREATE"

        # Create dabane se PEHLE ke field yaad rakho
        if before is None:
            before = self._field_ids()

        if not self._open_create(menu, label,
                                 plus_sel=(node or {}).get("plusSel", "")):
            self._mark("create", key, BLOCKED,
                       reason="create ka koi raasta nahi mila "
                              "('+' bhi nahi, Create button bhi nahi)")
            self.say(f"      [BLOCKED] {label} -- create form nahi khula")
            return None

        try:
            # Panel chipka ho to pehle hatao -- warna uske 280 element
            # form ke naam se save ho jayenge.
            self._close_settings_panel()

            # Ab bhi chipka hai? To ye data MILA-JULA hai -- form ka bhi
            # aur panel ka bhi. Aisa data save karna sabse bura hai: koi
            # test likhega "Sale Bill me Cursor wait on chuno", aur wo
            # Sale Bill ka field hai hi nahi.
            head_now = self._panel_heading()
            if "setting" in head_now.lower():
                self._mark("create", key, BLOCKED,
                           reason=f"Settings panel band nahi hua "
                                  f"({head_now[:40]!r}) -- form aur panel ka "
                                  f"mila-jula data save karne se behtar hai "
                                  f"chhod dena")
                self.say(f"      [BLOCKED] {label} -- Settings panel hata nahi")
                return None

            # ASLI SAWAAL: naye field aaye ya nahi?
            #
            # Heading par bharosa karna galat nikla. Store, Salt, Unit,
            # Manufacturer aur paanchon voucher ka form PANEL ki tarah
            # khulta hai -- list ka heading "Store List" waisa hi reh jata
            # hai. Isliye crawler ne list ke hi 254 element "create form"
            # ke naam se save kar diye.
            #
            # Naye field aana pakka signal hai: form khula to kuch naya
            # aayega, nahi khula to kuch nahi.
            after = self._field_ids()
            fresh = after - before
            if not fresh:
                self._mark("create", key, BLOCKED,
                           reason="create dabane par ek bhi naya field nahi "
                                  "aaya -- form khula hi nahi. List ke element "
                                  "'create form' ke naam se save karna galat "
                                  "hoga.")
                self.say(f"      [BLOCKED] {label} -- koi naya field nahi aaya")
                return None

            ok, head = self._form_matches(label, aliases)
            if not ok:
                self._mark("create", key, BLOCKED,
                           reason=f"'{label}' maanga tha par form "
                                  f"'{head}' ka khula -- galat data save "
                                  f"karne se behtar hai chhod dena")
                self.say(f"      [BLOCKED] {label} -- '{head}' ka form khula, "
                         f"chhod diya")
                return None

            data = collect(self.bp, deep=True, say=self.say)
            n = count_elements(data)
            q = data.get("quality") or {}
            st = PASS if q.get("level") == "ok" else PARTIAL
            row = {
                "id": key.replace(" > ", "/"),
                "menu": menu, "submenu": sub, "child": child,
                "name": f"{label} (Create)",
                "formType": "create",
                "formHeading": head,
                "url": (data.get("page") or {}).get("url", ""),
                "title": (data.get("page") or {}).get("title", ""),
                "heading": (data.get("page") or {}).get("heading", ""),
                "elements": n,
                # Jo field create dabane ke BAAD aaye -- yahi asli form hai.
                # Baaki list ke hain, jo peeche khuli rehti hai.
                "newFields": sorted(fresh),
                "newFieldCount": len(fresh),
                "inputs": data.get("inputs", []),
                "buttons": data.get("buttons", []),
                "dropdowns": data.get("dropdowns", []),
                "checkboxes": data.get("checkboxes", []),
                "links": (data.get("links") or [])[:400],
                "tables": data.get("tables", []),
                **collected_fields(data),
                "status": st,
            }
            self.pages.append(row)
            self._save_page(row)
            self._mark("create", key, st, elements=n, new_fields=len(fresh),
                       flags=q.get("flags"))
            self.say(f"      [{st}] {label} CREATE FORM -- {n} element "
                     f"({len(fresh)} naye)"
                     + (f", shak: {', '.join(q.get('flags') or [])}"
                        if st != PASS else ""))
            return row
        finally:
            # chahe kuch bhi ho, form band zaroor karo
            self._close_create()

    def _save_page(self, row: dict):
        """
        Har page ke turant baad likho -- sab aakhir me nahi.

        Crawler 20 minute chalta hai. Aakhir me save karne ka matlab hai ki
        browser crash hone par poora kaam gaya. Turant likhne se jo ho chuka
        wo bacha rehta hai.
        """
        f = OUT / "raw" / (row["id"].replace("/", "__") + ".json")
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(row, indent=1, ensure_ascii=False),
                     encoding="utf-8")
        self.state.setdefault("done", []).append(row["id"])
        self.state["lastPage"] = row["id"]
        self._save_state()

    # ---- control room ----

    def _do_control_room(self) -> dict:
        from framework import control_room as cr
        self.say("\nCONTROL ROOM")
        if not self._app_alive() and not self._revive():
            self._mark("control_room", "Control Room", BLOCKED,
                       reason="app band ho chuka tha -- koshish hi nahi ki")
            self.say("  [BLOCKED] app se koi jawab nahi")
            return {}
        self._home()
        try:
            if not cr.open_control_room(self.bp, verbose=self.verbose):
                self._mark("control_room", "Control Room", FAILED,
                           reason="khul nahi paya")
                self._shot("fail-control-room")
                self.say("  [FAIL] Control Room khul nahi paya")
                return {}
            data = cr.read(self.bp, verbose=False)
            got = extract(self.bp)

            out = {
                "readAt": data.get("read_at"),
                "total": data.get("total", 0),
                "known": data.get("settings", {}),
                "settings": data.get("raw", []),
                "dropdowns": got.get("dropdowns", []),
                "checkboxes": got.get("checkboxes", []),
                "inputs": got.get("inputs", []),
            }
            (OUT / "control-room.json").write_text(
                json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
            self._mark("control_room", "Control Room", PASS,
                       settings=out["total"])
            self.say(f"  [PASS] {out['total']} setting, "
                     f"{len(out['dropdowns'])} dropdown, "
                     f"{len(out['checkboxes'])} checkbox")
            return out
        except Exception as e:  # noqa: BLE001
            self._mark("control_room", "Control Room", FAILED, reason=str(e)[:200])
            self._shot("fail-control-room")
            self.say(f"  [FAIL] {str(e)[:100]}")
            return {}
        finally:
            safety.force_close_modal(self.page)

    # ---- poora crawl ----

    def _enable_settings(self):
        """
        Crawl se PEHLE settings ON karo -- taaki chhupe hue field bhi dikhein.

        Purani haalat backup me jaati hai, aur restore-settings.bat se wapas
        ki ja sakti hai. Crawl ke liye badli hui settings company me hamesha
        ke liye nahi rehni chahiye -- warna kal koi asli kaam karega aur
        socha kuch aur hoga.
        """
        from framework import control_room as cr
        only = list(cr.KNOWN) if self.enable == "known" else None
        what = ("sirf 15 jaani-pehchani settings" if self.enable == "known"
                else "HAR setting jisme 'Yes' ka vikalp hai")
        self.say(f"\nSETTINGS ON KAR RAHE HAIN ({what})")
        try:
            res = cr.enable_yes(self.bp, only=only, verbose=self.verbose)
        except cr.SettingLocked as e:
            self._mark("settings", "enable", SKIPPED, reason=str(e)[:200])
            self.say(f"  [SKIP] {str(e).splitlines()[0]}")
            return
        except Exception as e:  # noqa: BLE001
            self._mark("settings", "enable", FAILED, reason=str(e)[:200])
            self.say(f"  [FAIL] {str(e)[:120]}")
            return

        self._mark("settings", "enable", PASS, changed=res["changed"],
                   tried=res["tried"], failed=res["failed"],
                   app_back=res.get("app_back"))
        self.say(f"  [PASS] {res['changed']} setting badli "
                 f"({res['tried']} me se), {res['failed']} nahi ho payin")
        self.say(f"  Purani haalat: {res['backup']}")
        self.say(f"  Wapas karne ke liye: restore-settings.bat")

        # App reload ke baad WAAPAS aaya ya nahi -- ye jaanch zaroori hai.
        #
        # Pichhli baar reload nahi hua tha aur app aadhuri haalat me atak
        # gaya. Crawl phir bhi aage badha aur AATH menu "nahi mila" bola --
        # jabki menu the, app hi taiyaar nahi tha. Aakhir me browser band
        # ho gaya.
        #
        # App wapas na aaye to aage badhna bekaar hai: har page fail hoga
        # aur wajah kahin aur dhoondhi jayegi.
        if not res.get("app_back"):
            self.say("  !! App reload ke baad wapas nahi aaya.")
            self.say("     Ek baar aur intezaar kar rahe hain...")
            from framework import control_room as cr2
            self._home()
            if not cr2.wait_app_back(self.bp, timeout_ms=60000):
                self._mark("settings", "app-wapas", FAILED,
                           reason="reload ke baad app wapas nahi aaya -- "
                                  "aage badhna bekaar hai, har page fail hota")
                self.say("     App wapas nahi aaya. Crawl rok rahe hain.")
                self.say("     restore-settings.bat chala kar dobara koshish karo.")
                raise RuntimeError(
                    "Settings reload ke baad app wapas nahi aaya. "
                    "restore-settings.bat chalao, phir crawl dobara.")

        self._home()

    # ---- sidebar se list banana ----

    def _discover_sequence(self) -> dict:
        """
        Menu ki list live sidebar se banao (config sirf jaankari jodti hai).

        Sidebar na mile to purani config list par lautte hain -- aur bol kar,
        chupchaap nahi.
        """
        if not self._app_alive() and not self._revive():
            self.say("  (sidebar padh nahi paye: app se jawab nahi -- "
                     "config wali purani list chalegi)")
            return self.seq
        tree = discover_sidebar(self.page)
        if not tree:
            self.say("  (sidebar ka tree nahi mila -- config wali purani list chalegi)")
            return self.seq

        seq = build_sequence(tree, self.seq_config)
        planned, had = count_pages(seq), count_pages(self.seq_config)
        hidden = []

        def scan(nodes, trail):
            for x in nodes or []:
                p = trail + [x["name"]]
                if x.get("skip") and "chhupa" in str(x.get("skip_reason", "")):
                    hidden.append(" > ".join(p))
                scan(x.get("children"), p)
        for mm in seq["menus"]:
            if mm.get("skip") and "chhupa" in str(mm.get("skip_reason", "")):
                hidden.append(mm["name"])
            scan(mm.get("submenus"), [mm["name"]])

        missing = [mm["name"] for mm in seq["menus"] if mm.get("notInSidebar")]
        self.sidebar_info = {"pagesFromSidebar": planned, "pagesInConfig": had,
                             "hiddenInSidebar": hidden,
                             "configMenusNotInSidebar": missing}
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "sidebar.json").write_text(
            json.dumps(tree, indent=1, ensure_ascii=False), encoding="utf-8")
        self.say(f"\nSIDEBAR: {len(seq['menus'])} menu, {planned} page mile "
                 f"(config me {had} the)")
        if hidden:
            self.say(f"  chhupe hue ({len(hidden)}): {', '.join(hidden[:6])}"
                     + (" ..." if len(hidden) > 6 else ""))
        if missing:
            self.say("  config me hain par sidebar me nahi: " + ", ".join(missing))
        return seq

    def _crawl_nodes(self, top: str, nodes: list, mids: list, trail: list,
                     done: set):
        """
        Ek menu ke andar ka sab kuch -- group khol kar neeche, patta mile to
        page + (jahan ho) create form.

        top   -- upar ke menu ka naam
        mids  -- beech ke group (naam wale dict)
        trail -- ghar jaane ke baad dobara kholne wale group, upar se neeche
        """
        nodes = sorted(nodes, key=lambda x: x.get("order", 0))
        for i, s in enumerate(nodes, 1):
            label = s["name"]
            names = [g["name"] for g in mids] + [label]
            # (menu, sub, child) -- 3 se zyada gehra ho to beech wale jud jate hain
            sub = " > ".join(names[:-1]) if len(names) > 1 else label
            child = names[-1] if len(names) > 1 else ""
            key_txt = self._key(top, sub, child)
            slash = key_txt.replace(" > ", "/")
            self.say("    " + "  " * len(mids) + f"{i}/{len(nodes)}: {label}")

            if s.get("skip"):
                self._mark("page", key_txt, SKIPPED, reason=s.get("skip_reason", ""))
                self.say("      [SKIP] " + str(s.get("skip_reason", "")))
                continue

            kids = s.get("children") or []
            if kids:
                if not self._ensure_open(s):
                    self._mark("submenu", key_txt, FAILED, reason="nahi khula")
                    self.say(f"      [FAIL] '{label}' nahi khula")
                    continue
                self._crawl_nodes(top, kids, mids + [s], trail + [s], done)
                continue

            if s.get("emptyGroup"):
                self._mark("page", key_txt, SKIPPED,
                           reason="ye group hai par andar koi item nahi")
                self.say("      [SKIP] group khali hai")
                continue

            if slash in done:
                self.say("      (pehle ho chuka -- chhoda)")
                self._mark("page", slash, PASS, note="resume")
                continue

            self._trail = trail
            self._do_page(top, sub, child, node=s)
            if s.get("create") and (slash + "/CREATE") not in done:
                self._do_create(top, sub, child, before=self._field_ids(),
                                aliases=s.get("formNames"), node=s)
            self._reopen()

    def run(self) -> dict:
        t0 = time.time()
        if self.enable != "none":
            try:
                self._enable_settings()
            except RuntimeError as e:
                # App hi taiyaar nahi -- aage ka crawl bekaar hoga.
                # Jo settings badli hain wo backup me hain, isliye kuch
                # khoya nahi. Saaf batakar rukna hi sahi hai.
                self.say(f"\n{e}")
                return self._finish(time.time() - t0)
        if self.discover:
            self.seq = self._discover_sequence()
        menus = sorted(self.seq["menus"], key=lambda m: m["order"])
        total = len(menus)
        done = set(self.state.get("done", []))

        for m in menus:
            name, order = m["name"], m["order"]

            # Waqt ki seema. Ek crawl 28 GHANTE chal chuka hai -- uska koi
            # matlab nahi tha. Seema par pahunche to jo mila wo lekar
            # saaf ruk jao.
            if time.time() - t0 > self.budget_s:
                self._mark("menu", name, BLOCKED,
                           reason=f"waqt ki seema ({self.budget_s // 60} min) "
                                  f"khatam -- baaki menu chhode gaye",
                           order=order)
                self.say(f"\n!! {self.budget_s // 60} minute ho gaye -- "
                         f"crawl yahin rok rahe hain")
                for rest in menus[menus.index(m) + 1:]:
                    self._mark("menu", rest["name"], BLOCKED,
                               reason="waqt ki seema", order=rest["order"])
                break

            self.say(f"\nMENU {order}/{total}: {name}")

            # App zinda hai? Mari hui app par har menu 'nahi mila' dega
            # aur ghanton lag jayenge.
            if not self._app_alive() and not self._revive():
                self._mark("menu", name, FAILED,
                           reason="app se koi jawab nahi -- session khatam ho "
                                  "gaya. Aage ke menu koshish hi nahi kiye.",
                           order=order)
                self.say("  [FAIL] App se koi jawab nahi. Crawl rok rahe hain.")
                for rest in menus[menus.index(m) + 1:]:
                    self._mark("menu", rest["name"], BLOCKED,
                               reason="app band ho chuka tha",
                               order=rest["order"])
                break

            if m.get("skip"):
                self._mark("menu", name, SKIPPED,
                           reason=m.get("skip_reason", ""))
                self.say(f"  [SKIP] {m.get('skip_reason', '')}")
                continue

            self._home()
            ident = self._menu_identity(name, m.get("id", ""))
            if not ident:
                self._mark("menu", name, FAILED, reason="menu screen par nahi mila",
                           order=order)
                self._shot(f"fail-menu-{name}")
                self.say(f"  [FAIL] Menu #{order} '{name}' nahi mila")
                continue          # ek menu fail hone se baaki nahi rukte
            self.menus.append({**ident, "order": order})

            if not self._click_text(name, el_id=ident.get("id")
                                     or m.get("id", ""), sel=m.get("sel", "")):
                self._mark("menu", name, FAILED, reason="click nahi hua",
                           order=order)
                self._shot(f"fail-menu-{name}")
                self.say(f"  [FAIL] '{name}' khula nahi")
                continue
            self._mark("menu", name, PASS, order=order)
            self.say("  [PASS] menu khul gaya")

            subs = sorted(m.get("submenus", []), key=lambda s: s["order"])
            if m.get("leaf") and not subs:
                key = self._key(name)
                if key.replace(" > ", "/") in done:
                    self.say("      (pehle ho chuka -- chhoda)")
                    continue
                data = collect(self.bp, say=self.say)
                q = data.get("quality") or {}
                st = PASS if q.get("level") == "ok" else PARTIAL
                row = {"id": name, "menu": name, "submenu": "", "child": "",
                       "name": name,
                       "url": (data.get("page") or {}).get("url", ""),
                       "title": (data.get("page") or {}).get("title", ""),
                       "heading": (data.get("page") or {}).get("heading", ""),
                       "elements": count_elements(data),
                       **{k: data.get(k, []) for k in
                          ("inputs", "buttons", "dropdowns", "checkboxes",
                           "tables")},
                       "links": (data.get("links") or [])[:400],
                       **collected_fields(data),
                       "status": st}
                self.pages.append(row)
                self._save_page(row)
                self._mark("page", name, st, elements=row["elements"],
                           flags=q.get("flags"))
                self.say(f"      [{st}] {name} -- {row['elements']} element")
                continue

            # menu khulne par uske andar kya dikh raha hai
            expect = [s["name"] for s in subs]
            seen = self._submenus_on_screen(expect)
            missing = [s["name"] for s in seen if not s["onScreen"]]
            if missing:
                self.say(f"      (screen par nahi dikhe: {', '.join(missing[:5])})")

            # Ye menu ab khula hai. Neeche ke saare group/page ek-ek karke --
            # kitni bhi gehrai ho (sidebar me nested menu hote hain).
            top_node = {"name": name,
                        "id": ident.get("id") or m.get("id", ""),
                        "sel": m.get("sel", "")}
            self._trail = [top_node]
            self._crawl_nodes(name, subs, [], [top_node], done)

        self.control_room = self._do_control_room()
        return self._finish(time.time() - t0)

    # ---- report ----

    def _finish(self, seconds: float) -> dict:
        n = lambda kind, st: sum(1 for x in self.status  # noqa: E731
                                 if x["type"] == kind and x["status"] == st)
        summary = {
            "scannedAt": time.strftime("%Y-%m-%d %H:%M"),
            "seconds": round(seconds, 1),
            "totalMenus": len([m for m in self.seq["menus"]]),
            "menusPassed": n("menu", PASS),
            "menusFailed": n("menu", FAILED),
            "menusSkipped": n("menu", SKIPPED),
            "pagesPassed": n("page", PASS),
            "pagesFailed": n("page", FAILED),
            "pagesPartial": n("page", PARTIAL) + n("create", PARTIAL),
            "pagesBlocked": n("page", BLOCKED),
            "newFields": sum(x.get("new_fields", 0) for x in self.status
                             if x["type"] == "create"),
            "createFormsPassed": n("create", PASS),
            "createFormsBlocked": n("create", BLOCKED),
            "elements": sum(p.get("elements", 0) for p in self.pages),
            "settingsChanged": sum(1 for x in self.status
                                   if x["type"] == "settings"
                                   and x["status"] == PASS
                                   for _ in [0]) and next(
                (x.get("changed", 0) for x in self.status
                 if x["type"] == "settings"), 0),
            "controlRoomSettings": self.control_room.get("total", 0),
            "controlRoomDropdowns": len(self.control_room.get("dropdowns", [])),
            "pagesPlanned": count_pages(self.seq),
            "discovered": self.discover,
            **{k: v for k, v in self.sidebar_info.items()},
            # BLOCKED ko fail nahi maante -- wo item is company me hai hi
            # nahi (permission ya trade ke hisaab se). Wo app ki galti nahi.
            # PARTIAL page bhi "poora PASS" nahi hai -- shak wala data chupna nahi chahiye
            "status": ("PASS" if n("menu", FAILED) == 0 and n("page", FAILED) == 0
                       and n("page", PARTIAL) == 0 and n("create", PARTIAL) == 0
                       else "PARTIAL"),
        }

        # Ek khali crawl pichhle ACHHE crawl ko mita na de. (Pehle yahi hua:
        # session mar gaya, 0 page mile, aur purana data bhi saaf ho gaya.)
        def target(name: str):
            f = OUT / name
            if not self.pages and f.exists() and f.stat().st_size > 80:
                self.say(f"  ({name}: is baar kuch nahi mila, isliye purana nahi mitaya "
                         f"-- naya {name[:-5]}.last-failed.json me)")
                return OUT / (name[:-5] + ".last-failed.json")
            return f

        target("menus.json").write_text(
            json.dumps(self.menus, indent=1, ensure_ascii=False), encoding="utf-8")
        target("pages.json").write_text(
            json.dumps(self.pages, indent=1, ensure_ascii=False), encoding="utf-8")
        (OUT / "crawl-summary.json").write_text(
            json.dumps({**summary, "items": self.status}, indent=1,
                       ensure_ascii=False), encoding="utf-8")

        meta = {
            "application": {"name": "MargBooks", "baseUrl": settings.BASE_URL,
                            "scannedAt": summary["scannedAt"]},
            "menus": self.menus,
            "pages": [{k: v for k, v in p.items()
                       if k not in ("inputs", "buttons", "dropdowns",
                                    "checkboxes", "links", "tables", "clickables",
                                    "customSelects", "tabs", "collapsers",
                                    "gridColumns")}
                      for p in self.pages],
            "inputs": [i for p in self.pages for i in p.get("inputs", [])],
            "buttons": [b for p in self.pages for b in p.get("buttons", [])],
            "dropdowns": [d for p in self.pages for d in p.get("dropdowns", [])],
            "checkboxes": [c for p in self.pages for c in p.get("checkboxes", [])],
            "links": [l for p in self.pages for l in p.get("links", [])],
            "tables": [t for p in self.pages for t in p.get("tables", [])],
            "clickables": [c for p in self.pages for c in p.get("clickables", [])],
            "customSelects": [c for p in self.pages for c in p.get("customSelects", [])],
            "tabs": [c for p in self.pages for c in p.get("tabs", [])],
            "collapsers": [c for p in self.pages for c in p.get("collapsers", [])],
            "gridColumns": [{**c, "page": p["id"]} for p in self.pages
                            for c in p.get("gridColumns", [])],
            "controlRoom": self.control_room,
            "crawlStatus": summary,
        }
        target("metadata.json").write_text(
            json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")

        logbook.write("scanner", "crawl", summary["status"],
                      duration=seconds, pages=len(self.pages),
                      elements=summary["elements"])
        return summary
