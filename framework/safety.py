"""
Suraksha ki parat -- POORE browser pe, HAR page pe, HAMESHA.

Pehle guard sirf Organisation page pe lagta tha, isliye Item List pe delete
click ho gaya. Ab ye `add_init_script` se lagta hai -- matlab har naye page,
har navigation, har iframe pe apne aap chalu ho jata hai. Bhoolne ka sawaal
hi nahi.

Do parat:
  1. Browser ke andar (JS): delete/remove type ke har button ko na-clickable
     bana do, aur capture phase me unka click nigal jao.
  2. Python taraf: click karne se PEHLE check karo ki jis cheez pe click ho
     raha hai wo khatarnak to nahi. Shak ho to ruk jao, andaza mat lagao.
"""
from __future__ import annotations

import re
from playwright.sync_api import Page, Locator

from config.settings import settings


class UnsafeClick(RuntimeError):
    """Robot ek khatarnak button pe click karne wala tha -- roka gaya."""


# class/id me ye shabd = khatra
DANGER_ATTR = re.compile(
    r"(del(ete)?|trash|remove|discard|destroy|erase|purge|cancel-?bill|void)",
    re.I,
)
# button ka text = khatra
DANGER_TEXT = {
    "delete", "remove", "discard", "trash", "erase",
    "delete all", "remove all", "clear all", "reset all",
    "हटाएं", "मिटाएं",
}

GUARD_JS = r"""
(() => {
  if (window.__mbQaGuard) return;
  window.__mbQaGuard = true;

  const DANGER = /(del(ete)?|trash|remove|discard|destroy|erase|purge|void)/i;
  const DANGER_TEXT = /^(delete|remove|discard|erase|delete all|remove all)$/i;

  const isDanger = (el) => {
    if (!el || !el.getAttribute) return false;
    const bag = [
      el.className && typeof el.className === 'string' ? el.className : '',
      el.id || '',
      el.getAttribute('title') || '',
      el.getAttribute('aria-label') || '',
      el.getAttribute('data-action') || '',
    ].join(' ');
    if (DANGER.test(bag)) return true;
    const txt = (el.innerText || '').trim();
    return txt.length < 20 && DANGER_TEXT.test(txt);
  };

  // 1. capture phase -- click page tak pahunchne hi mat do
  document.addEventListener('click', (e) => {
    let n = e.target;
    for (let i = 0; n && i < 5; i++, n = n.parentElement) {
      if (isDanger(n)) {
        e.stopImmediatePropagation();
        e.preventDefault();
        console.warn('[MB-QA-GUARD] blocked click on', n.className || n.id || n.innerText);
        window.__mbQaBlocked = (window.__mbQaBlocked || 0) + 1;
        return;
      }
    }
  }, true);

  // 2. DELETE CONFIRMATION -> apne aap "No"
  //
  // Kaaran chahe kuch bhi ho -- humara click, koi keyboard shortcut, ya app
  // ka apna code -- ye popup dikhte hi "No" daba dega. Isse do faayde:
  //   (a) kuch delete nahi hoga
  //   (b) popup screen pe atak kar baaki test nahi rokega
  //
  // Dhyaan: sirf DELETE/REMOVE wale popup. "Transaction data will be loss,
  // are you sure you want to close" wale exit-popup ko haath nahi lagate --
  // usme "Yes" chahiye hota hai aur wo Python taraf handle hota hai.
  const DEL_CONFIRM = /\b(delete|remove|mitao|hataa?o)\b/i;
  window.__mbDeleteBlocked = 0;
  window.__mbDeleteLog = [];

  const answerNo = () => {
    const boxes = document.querySelectorAll(
      '.modal, [role="dialog"], ngb-modal-window, .swal2-popup, .confirm-box');
    for (const box of boxes) {
      if (!box.offsetHeight) continue;
      const txt = (box.innerText || '').replace(/\s+/g, ' ').trim();
      if (!DEL_CONFIRM.test(txt)) continue;
      const btns = [...box.querySelectorAll('button, a, .btn, input[type="button"]')]
        .filter(b => b.offsetHeight > 0);
      const no = btns.find(b => /^(no|cancel|nahi|close)$/i.test((b.innerText || b.value || '').trim()));
      if (!no) continue;
      window.__mbDeleteBlocked++;
      window.__mbDeleteLog.push({
        at: Date.now(),
        text: txt.slice(0, 150),
        buttons: btns.map(b => (b.innerText || b.value || '').trim()).slice(0, 5),
        // popup se PEHLE kya hua -- kaaran yahin se pata chalega
        recent: (window.__mbEvents || []).slice(-5),
      });
      console.warn('[MB-QA-GUARD] delete confirmation -> No dabaya');
      no.click();
      return;
    }
  };

  // 3. pointer-events band -- galti se mouse waha ja hi na sake
  const disarm = () => {
    document.querySelectorAll('button, a, i, svg, span, td').forEach(el => {
      if (isDanger(el)) {
        el.style.pointerEvents = 'none';
        el.setAttribute('data-mb-qa-disarmed', '1');
      }
    });
  };
  const boot = () => {
    disarm();
    answerNo();
    new MutationObserver(() => { disarm(); answerNo(); }).observe(
      document.documentElement, {childList: true, subtree: true});
    // MutationObserver kabhi-kabhi chook jata hai (animation/detached node),
    // isliye ek dheema safety-net bhi.
    setInterval(answerNo, 400);
  };
  if (document.body) boot();
  else document.addEventListener('DOMContentLoaded', boot);
})();
"""


def arm_context(context):
    """
    Browser context pe guard lagao. Ye HAR page aur HAR navigation pe apne aap
    chalega -- ek baar lagao, bhool jao.

    ALLOW_DESTRUCTIVE=true hone par guard nahi lagta (jaan-boojh kar).
    """
    if settings.ALLOW_DESTRUCTIVE:
        print("  [safety] ALLOW_DESTRUCTIVE=true -- guard OFF. Data badal sakta hai!")
        return False
    context.add_init_script(GUARD_JS)
    watch_toasts(context)
    return True


def blocked_count(page: Page) -> int:
    """Guard ne ab tak kitne khatarnak click roke."""
    try:
        return page.evaluate("() => window.__mbQaBlocked || 0")
    except Exception:  # noqa: BLE001
        return 0


def describe(loc: Locator) -> dict:
    """Element ka parichay -- click se pehle dekhne ke liye."""
    try:
        return loc.evaluate("""
          e => ({
            tag: e.tagName.toLowerCase(),
            id: e.id || '',
            cls: (typeof e.className === 'string' ? e.className : '') || '',
            title: e.getAttribute('title') || '',
            aria: e.getAttribute('aria-label') || '',
            text: (e.innerText || e.value || '').trim().slice(0, 40),
            disarmed: e.getAttribute('data-mb-qa-disarmed') === '1',
          })
        """)
    except Exception:  # noqa: BLE001
        return {}


def assert_safe(loc: Locator, key: str = ""):
    """
    Click se PEHLE janch. Khatarnak laga to UnsafeClick uthao.

    Yahi wo cheez hai jo pehle nahi thi: robot andhere me click kar deta tha.
    Ab wo pehle dekhta hai ki main kis cheez pe click karne ja raha hoon.
    """
    if settings.ALLOW_DESTRUCTIVE:
        return
    d = describe(loc)
    if not d:
        return
    bag = " ".join([d.get("cls", ""), d.get("id", ""),
                    d.get("title", ""), d.get("aria", "")])
    text = (d.get("text") or "").strip().lower()

    if DANGER_ATTR.search(bag) or text in DANGER_TEXT or d.get("disarmed"):
        raise UnsafeClick(
            f"RUKO -- '{key or 'element'}' ek khatarnak button pe ja raha tha:\n"
            f"    <{d.get('tag')}> id={d.get('id')!r} class={d.get('cls')!r} "
            f"text={d.get('text')!r}\n"
            f"  Ya to locator galat hai, ya page badal gaya hai. Click nahi kiya."
        )


# ---- "You are not authorized" ----

NOT_AUTHORIZED = (
    "not authorized", "you are not authorized", "access denied",
    "permission denied", "no rights", "unauthorized",
)


class ModuleNotEnabled(Exception):
    """Module Control Room me OFF hai -- ye BUG NAHI hai, test skip hona chahiye."""


def check_authorized(page: Page, screen: str = ""):
    """
    MargBooks me bahut module Control Room se enable karne padte hain. Off ho
    to 'Oops! You are not authorized' aata hai. Ye bug nahi -- setting hai.
    Isliye test FAIL nahi, SKIP hona chahiye, warna asli bug 50 red me dab jate hain.
    """
    try:
        body = (page.inner_text("body") or "").lower()
    except Exception:  # noqa: BLE001
        return
    for phrase in NOT_AUTHORIZED:
        if phrase in body:
            raise ModuleNotEnabled(
                f"'{screen or page.url}' is account pe enable nahi hai "
                f"(MargBooks bola: 'not authorized').\n"
                f"  Control Room / Settings me ye module ON karo, phir test chalega."
            )


# ---- App ke apne Yes/No popup ----

def read_modal(page) -> dict | None:
    """Screen pe koi app-modal khula hai? Uska text aur buttons batao."""
    try:
        return page.evaluate(r"""
          () => {
            const sels = 'ngb-modal-window, .modal, .modal-dialog, [role="dialog"], '
                       + '.swal2-popup, .ui-dialog, .confirm-box, [class*="popup"]';
            const box = [...document.querySelectorAll(sels)]
              .find(e => e.offsetHeight > 0 && getComputedStyle(e).display !== 'none');
            if (!box) return null;
            const btns = [...box.querySelectorAll('button, a.btn, input[type="button"]')]
              .filter(b => b.offsetHeight > 0)
              .map(b => (b.innerText || b.value || '').replace(/\s+/g,' ').trim())
              .filter(Boolean);
            return {text: (box.innerText||'').replace(/\s+/g,' ').trim().slice(0,200),
                    buttons: btns};
          }
        """)
    except Exception:  # noqa: BLE001
        return None


def dismiss_modal(page, verbose: bool = False) -> bool:
    """
    App ka Yes/No popup band karo -- BINA data save kiye.

    Faisla text padh kar hota hai, andha-dhundh Yes nahi:
      "Save changes?"                     -> NO   (warna data likha jayega)
      "Transaction data will be loss..."  -> YES  (bas form band hoga)
      kuch samajh na aaye                 -> NO   (surakshit taraf)

    Button seedha popup ke ANDAR se uthaya jata hai. Pehle get_by_role se
    dhoondhte the, par MargBooks ke Yes/No asli <button> nahi hain -- isliye
    mil hi nahi rahe the aur popup khula reh jata tha.
    """
    m = read_modal(page)
    if not m or not m.get("buttons"):
        return False

    text = (m["text"] or "").lower()

    # Yes ka matlab "save ho jayega"? Tab No dabao.
    wants_save = any(w in text for w in
                     ("save", "store", "update", "post", "submit", "sahej"))
    # Yes ka matlab "sirf band/discard hoga"? Tab Yes surakshit hai.
    wants_exit = any(w in text for w in
                     ("exit", "close", "discard", "leave", "will be loss",
                      "data will be lost", "cancel", "are you sure", "band"))

    if wants_save and not wants_exit:
        prefer = ["no", "cancel", "don't save", "dont save", "nahi"]
    elif wants_exit:
        prefer = ["yes", "ok", "exit", "discard", "close", "haan"]
    else:
        prefer = ["no", "cancel", "close", "nahi"]

    # popup ke andar se hi button uthao -- tag/role kuch bhi ho, farak nahi
    handle = page.evaluate_handle(
        r"""
        (prefs) => {
          const sels = 'ngb-modal-window, .modal, .modal-dialog, [role="dialog"], '
                     + '.swal2-popup, .ui-dialog, .confirm-box, [class*="popup"]';
          const box = [...document.querySelectorAll(sels)]
            .find(e => e.offsetHeight > 0 && getComputedStyle(e).display !== 'none');
          if (!box) return null;
          const norm = t => (t || '').replace(/\s+/g, ' ').trim().toLowerCase();
          const clickable = [...box.querySelectorAll(
            'button, a, input[type="button"], input[type="submit"], [role="button"], .btn')]
            .filter(b => b.offsetHeight > 0);
          for (const want of prefs) {
            const hit = clickable.find(b => norm(b.innerText || b.value) === want);
            if (hit) return hit;
          }
          return null;
        }
        """,
        prefer,
    )
    el = handle.as_element()
    if el:
        try:
            audit_click(el, "modal.button")
            el.click(timeout=3000)
            page.wait_for_timeout(1000)
            if verbose:
                print(f"  [modal] {m['text'][:55]!r} -> dabaya (rule: {prefer[0]})")
            return True
        except Exception:  # noqa: BLE001
            try:                       # overlay beech me ho to force
                el.click(timeout=2000, force=True)
                page.wait_for_timeout(1000)
                return True
            except Exception:  # noqa: BLE001
                pass

    if verbose:
        print(f"  [modal] band nahi kar paye: {m['text'][:70]!r} buttons={m['buttons']}")
    return False


def _transaction_form_open(page) -> bool:
    """
    Koi bill/voucher ka form khula hai?

    Iski pehchan: header ka ledger field ya form ke Save/Close button.
    Inme se kuch bhi ho to Escape KHATARNAK hai -- wo form band kar dega.
    """
    try:
        return bool(page.evaluate("""() => !!(
            document.querySelector('[id^="txtLedgerName"]') ||
            document.querySelector('[id^="btnSave"]') ||
            document.querySelector('[id^="btnEsc"]') ||
            document.querySelector('[id^="txt-itemLinkID"]')
        )"""))
    except Exception:  # noqa: BLE001
        return False


def force_close_modal(page, verbose: bool = False) -> bool:
    """
    Aakhri raasta: popup ka X ya Escape. Yes/No ko haath nahi lagate,
    kyunki hume pata nahi unka matlab kya hai.

    Sale Bill pe ek "warning" wala ngb-modal aata tha jo click rok deta tha
    aur band nahi ho raha tha. Isliye ab zyada tareeke, aur aakhir me
    CONFIRM bhi karte hain ki wo sach me gaya ya nahi.
    """
    sels = (
        "ngb-modal-window .close", "ngb-modal-window button.btn-close",
        'ngb-modal-window button[aria-label="Close"]',
        ".modal .close", '[role="dialog"] .close',
        '.modal button[aria-label="Close"]', ".swal2-close",
        "#btn-Close", "button.btn-close",
    )
    for sel in sels:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=600):
                audit_click(el, f"modal.close:{sel}")
                el.click(timeout=2000)
                page.wait_for_timeout(800)
                return True
        except Exception:  # noqa: BLE001
            continue
    # Text se Close/Cancel dhoondho (Yes/No ko chhod kar)
    for label in ("Close", "Cancel", "Ok", "OK"):
        try:
            btn = page.get_by_role("button", name=label, exact=True).first
            if btn.is_visible(timeout=500):
                btn.click(timeout=1500)
                page.wait_for_timeout(700)
                if read_modal(page) is None:
                    return True
        except Exception:  # noqa: BLE001
            continue

    # Escape SIRF tab jab koi transaction form khula na ho.
    #
    # ASLI BUG: Sale Bill khula tha, ag-Grid ban chuka tha, aur maine popup
    # band karne ke liye Escape daba diya. MargBooks me transaction form par
    # Escape popup band nahi karta -- POORA BILL band kar deta hai. Phir
    # "data will be lost" wali confirmation aayi, uspe bhi Escape pada, aur
    # bill chala gaya.
    #
    # Uske baad test ne kaha "form khula hi nahi" -- jabki maine khud band
    # kiya tha. Ye sabse mehnga tarah ka bug hai: galti apni, ilzaam app par.
    if _transaction_form_open(page):
        left = read_modal(page)
        if left and verbose:
            print(f"  [modal] form khula hai, isliye Escape nahi dabaya. "
                  f"Popup: {left.get('text', '')[:90]!r}")
        return left is None

    for _ in range(2):
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(700)
        except Exception:  # noqa: BLE001
            break
        if read_modal(page) is None:
            return True

    left = read_modal(page)
    if left and verbose:
        print(f"  [modal] band nahi hua: {left.get('text', '')[:110]!r} "
              f"buttons={left.get('buttons')}")
    return left is None


# ---- Click audit + toast capture ----
#
# "Pre-Defined Ledger Data Can't Be Deleted!" toast dikha tha -- matlab kahin
# delete dabaya gaya. Andaza lagane ke bajaye har click ka hisaab rakhte hain.

CLICK_LOG: list[dict] = []


def audit_click(loc, key: str = ""):
    """Har click se pehle: kis element pe ja raha hai, wo file me likh do."""
    import time as _t
    d = describe(loc)
    entry = {"t": round(_t.time(), 2), "key": key,
             "tag": d.get("tag"), "id": d.get("id"),
             "cls": d.get("cls"), "text": d.get("text")}
    CLICK_LOG.append(entry)
    return entry


def flush_click_log():
    """Saare clicks artifacts/clicks.log me likh do."""
    if not CLICK_LOG:
        return None
    path = settings.ARTIFACTS / "clicks.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{e['t']}  key={e['key']:<24} <{e['tag']}> id={e['id']!r} "
             f"class={e['cls']!r} text={e['text']!r}" for e in CLICK_LOG]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


TOAST_JS = r"""
() => {
  if (window.__mbToastHook) return;
  window.__mbToastHook = true;
  window.__mbToasts = [];
  // every time a message appears is kept (with its time), also when the same text comes again later:
  // a test checks a toast that the app shows for ~3 s, which may be gone by the time the check runs.
  const last = new WeakMap();
  const grab = () => {
    document.querySelectorAll(
      '.toast, [class*="toast"], .alert, [class*="snack"], [class*="notify"]'
    ).forEach(e => {
      const t = (e.innerText||'').replace(/\s+/g,' ').trim();
      if (t && t.length < 200 && last.get(e) !== t) {
        last.set(e, t);
        window.__mbToasts.push({t, at: Date.now()});
        if (window.__mbToasts.length > 300) window.__mbToasts.splice(0, 100);
      }
    });
  };
  new MutationObserver(grab).observe(document.documentElement,
                                     {childList: true, subtree: true});
  grab();
}
"""


def watch_toasts(context):
    """App ke saare toast/alert message record karo -- chupi hui galtiyan pakadne ke liye."""
    context.add_init_script(TOAST_JS)


def get_toasts(page) -> list[dict]:
    try:
        return page.evaluate("() => window.__mbToasts || []")
    except Exception:  # noqa: BLE001
        return []


def guarded_click(loc, key: str = "", inside_modal: bool = False, **kw):
    """
    Janch + hisaab + click -- ek hi jagah. Har page object yahi use kare.

    Click se pehle raasta bhi saaf karta hai: koi modal khula reh gaya ho to
    Playwright ka click "modal intercepts pointer events" keh kar 15 second
    tak atak jata hai. Ek baar delete-popup ki wajah se poora run ruk gaya tha.

    inside_modal=True -- jab button MODAL KE ANDAR hi ho.
    ====================================================
    ASLI BUG: Purchase Bill par ek popup aata hai --
        "How would you like to create your purchase bill?"
        [Upload & Auto Read Invoice]  [Start Manual Entry]

    "Start Manual Entry" dabana hi tha, par guard ne pehle POPUP BAND karne
    ki koshish ki. Popup band nahi hua (peeche form khula tha, isliye Escape
    bhi mana hai), aur guard ne UnsafeClick utha diya.

    Natija: Purchase ke SAATON form nahi khule -- aur wajah app nahi, mera
    apna guard tha. Raasta saaf karne wala hi raste me aa gaya.

    Jab hum jaan-boojh kar modal ke andar ka button daba rahe hain, to use
    band karna galat hai. Jaanch (delete-guard, hisaab) phir bhi lagti hai.
    """
    page = getattr(loc, "page", None)
    if page is not None and not inside_modal and read_modal(page):
        if not (dismiss_modal(page) or force_close_modal(page, verbose=True)):
            m = read_modal(page) or {}
            raise UnsafeClick(
                "Ek popup khula hai jo click rok raha hai aur band nahi ho raha.\n"
                f"  Popup keh raha hai: {m.get('text', '')[:200]!r}\n"
                f"  Buttons: {m.get('buttons')}\n"
                "  Ye text mujhe bhejo -- iske hisaab se niyam jod dunga."
            )
        page.wait_for_timeout(400)
    assert_safe(loc, key)
    audit_click(loc, key)
    loc.click(**kw)


def audit_key(key_name: str, where: str = ""):
    """Keyboard press ka bhi hisaab -- Escape/Delete jaise keys shortcut fire karte hain."""
    import time as _t
    CLICK_LOG.append({"t": round(_t.time(), 2), "key": f"KEYBOARD:{where}",
                      "tag": "key", "id": "", "cls": "", "text": key_name})


# ---- Delete confirmation ka hisaab ----

def delete_attempts(page) -> list[dict]:
    """Kitni baar delete-confirmation aayi aur usse pehle kya hua tha."""
    try:
        return page.evaluate("() => window.__mbDeleteLog || []")
    except Exception:  # noqa: BLE001
        return []


def delete_report(page, path):
    """
    Delete popup ka poora record likho -- yahi batayega ki wo kyun aa raha hai.
    Har entry me popup se pehle ke 5 events hote hain (click/keyboard).
    """
    log = delete_attempts(page)
    if not log:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"DELETE CONFIRMATION -- {len(log)} baar aayi, har baar 'No' dabaya",
             "har entry ke neeche popup se PEHLE ke events hain (yahi kaaran batayenge)",
             ""]
    for i, d in enumerate(log, 1):
        lines.append(f"--- #{i}  at {d.get('at')} ---")
        lines.append(f"  popup  : {d.get('text')}")
        lines.append(f"  buttons: {d.get('buttons')}")
        lines.append("  popup se pehle ke events:")
        for e in d.get("recent", []):
            if e.get("type") == "key":
                lines.append(f"    KEY   {e.get('key')}  trusted={e.get('trusted')}  "
                             f"on={e.get('target')}")
            else:
                lines.append(f"    CLICK trusted={e.get('trusted')} "
                             f"danger={e.get('danger')} target={e.get('target')}")
                if e.get("stack"):
                    lines.append(f"          stack: {e.get('stack')}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def delete_count(page) -> int:
    try:
        return page.evaluate("() => window.__mbDeleteBlocked || 0")
    except Exception:  # noqa: BLE001
        return 0


def safe_clear(el, page=None):
    """
    Input saaf karo -- BINA Delete key dabaye.

    ASLI BUG YAHI THA. Playwright ka el.fill("") andar-andar select-all + DELETE
    key dabata hai. MargBooks ke list page pe Delete key ka matlab hai "selected
    row delete karo" -- chahe cursor search box me ho. Isliye har search par
    "Are you sure you want to delete the selected Record?" popup aa raha tha.
    Ye humara bug tha, app ka nahi.

    Ab value seedha JS se khali karte hain aur Angular ke liye input/change
    event bhej dete hain. Koi keyboard event nahi -> koi shortcut nahi fire hota.
    """
    el.evaluate("""
      (e) => {
        // A wrapper (div/span with the same id) may hold the real input: clear that one.
        if (!/^(INPUT|TEXTAREA|SELECT)$/.test(e.tagName)) {
          const inner = e.querySelector('input, textarea');
          if (!inner) return;
          e = inner;
        }
        const proto = e.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype
                    : e.tagName === 'SELECT' ? window.HTMLSelectElement.prototype
                    : window.HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
        setter.call(e, '');                       // Angular ko dikhe
        e.dispatchEvent(new Event('input',  {bubbles: true}));
        e.dispatchEvent(new Event('change', {bubbles: true}));
        // Kuch grid (keyup) pe filter chalate hain, (input) pe nahi. Isliye
        // keyup bhi bhejo -- par ek HARMLESS key se. 'Delete' kabhi nahi,
        // warna wahi row-delete wala bug wapas aa jayega.
        e.dispatchEvent(new KeyboardEvent('keyup',
          {bubbles: true, key: 'a', code: 'KeyA'}));
      }
    """)
    if page is not None:
        page.wait_for_timeout(200)
