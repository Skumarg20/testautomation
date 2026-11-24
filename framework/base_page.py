"""Thin wrapper over Playwright Page that resolves logical keys via LocatorStore."""
from __future__ import annotations

import logging
from playwright.sync_api import Page, Locator, TimeoutError as PWTimeout

from config.settings import settings
from framework.locator_store import store, LocatorNotFound
from framework import safety

log = logging.getLogger("mb")


class BasePage:
    def __init__(self, page: Page):
        self.page = page
        self.page.set_default_timeout(settings.TIMEOUT)

    # ---------- resolution ----------

    _SEL_START = ("#", "[", ".", "//", "xpath=", "css=", "role=", "text=", "label=", "nearlabel=",
                  "placeholder=", "testid=", "exact_text=", "input", "button", "select", "textarea", "a[")

    # A logical key is exactly "page.element" (identifiers). Anything else is a selector. "a.dropdown-toggle"
    # looks like a key but its first part is an HTML tag: it is CSS. (Treated as a key it was "learned" into
    # the registry as page 'a' and polluted it.)
    _KEY_RE = __import__("re").compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")
    _HTML_TAGS = {"a", "b", "i", "p", "div", "span", "button", "input", "select", "textarea", "label", "li", "ul",
                  "ol", "td", "th", "tr", "table", "tbody", "thead", "img", "svg", "form", "nav", "h1", "h2", "h3",
                  "h4", "h5", "h6", "em", "strong", "small", "section", "header", "footer", "option", "mat", "ng"}

    @classmethod
    def looks_like_selector(cls, key: str) -> bool:
        """'sale.save' is a logical key; '[id^="btnSave"]', 'role=button:Save', 'a.menulink' are selectors."""
        k = str(key or "").strip()
        if not cls._KEY_RE.match(k):
            return True
        page = k.split(".", 1)[0]
        if page in store._data:              # a registry section (nav, sale, item, ...): logical key
            return False
        return page.lower() in cls._HTML_TAGS

    # Registry entries the self-healing must never change: the side menu and the login form. A healed "nav.sale"
    # once became the dashboard's "Create Sale Bill" button, so every Sale > Return opened a Sale Bill.
    PINNED = ("nav.", "login.")

    @staticmethod
    def _first_visible(loc: Locator) -> Locator:
        """The first match that is on screen. With two bills open in tabs (Sale Return + Sale Bill) every field
        exists twice and the hidden tab's copy comes first in the page: clicking `.first` hit the hidden one
        (TC_SALE_051 'input.mydate'). One match, or none visible: `.first` as before."""
        try:
            n = loc.count()
            if n > 1:
                for i in range(min(n, 20)):
                    if loc.nth(i).is_visible():
                        return loc.nth(i)
        except Exception:  # noqa: BLE001
            pass
        return loc.first

    def find(self, key: str, probe_ms: int = 2500, want: str = "any") -> Locator:
        """
        Logical key -> Locator. Har candidate selector ko chhote timeout ke saath
        probe karta hai; jo mila usko promote kar deta hai.
        """
        last_err = None
        pinned = str(key).startswith(self.PINNED)
        if self.looks_like_selector(key) and not pinned:
            loc = self._to_locator(key)
            loc.first.wait_for(state="attached", timeout=max(probe_ms, 5000))
            return self._first_visible(loc)
        try:
            candidates = store.candidates(key)
        except LocatorNotFound:
            # Test Studio steps carry a real selector ('[formcontrolname="x"]', '#id',
            # 'role=button:Save'), not a logical key. Use it directly.
            if self.looks_like_selector(key):
                loc = self._to_locator(key)
                loc.first.wait_for(state="attached", timeout=max(probe_ms, 5000))
                return self._first_visible(loc)
            # key locators file me hai hi nahi -- seekh lo
            learned = self._learn(key, want)
            if learned:
                return self._to_locator(learned).first
            raise
        for sel in candidates:
            try:
                loc = self._to_locator(sel)
                loc.first.wait_for(state="attached", timeout=probe_ms)
                # promote only what is really on screen: a hidden element that merely exists in the page
                # (a Control Room select, a dashboard tile) must not become the first choice
                if not pinned and loc.first.is_visible():
                    store.promote(key, sel)
                return loc.first
            except (PWTimeout, Exception) as e:  # noqa: BLE001
                last_err = e
                continue
        if pinned:                  # fixed entries: never guessed, never rewritten
            raise LocatorNotFound(f"'{key}': none of its fixed selectors is in the page ({last_err})")
        # 1. Catalogue me dekho -- shayad ye field pehle kisi run me dekha ho.
        # Registry me har element ke KAI raaste hote hain. App badalne par
        # aksar ek hi tootta hai -- isliye ek-ek karke sab try karte hain.
        for cat_sel in self._catalogue_selectors(key, want):
            try:
                loc = self._to_locator(cat_sel).first
                loc.wait_for(state="attached", timeout=probe_ms)
                if not loc.is_visible():                        # only what is on screen is learned
                    continue
                store.add(key, [cat_sel] + list(candidates))   # yaad rakh lo
                store.save()
                log.info(f"  [registry] {key} -> {cat_sel}")
                return loc
            except Exception:  # noqa: BLE001
                continue

        # 2. Source se nikaale hue metadata me dekho.
        # Source SAB screens jaanta hai -- wo bhi jahan agent kabhi pahuncha
        # hi nahi. Isliye ye browser wale catalogue se pehle nahi, par
        # andaza lagane se pehle zaroor.
        for meta_sel in self._metadata_selectors(key, want):
            try:
                loc = self._to_locator(meta_sel).first
                loc.wait_for(state="attached", timeout=probe_ms)
                store.add(key, [meta_sel] + list(candidates))
                store.save()
                log.info(f"  [metadata] {key} -> {meta_sel}")
                return loc
            except Exception:  # noqa: BLE001
                continue

        # 3. Ab bhi na mile to page pe khud dhoondho.
        # Testers saadhi bhasha me likhte hain -- locators ka intezaam tool ka
        # kaam hai, unka nahi.
        learned = self._learn(key, want)
        if learned:
            return self._to_locator(learned).first

        # 4. Sab niyam fail. Ab AI se poochho -- yahi AAKHRI raasta hai.
        # Upar wale sab har baar ek jaisa natija dete hain aur muft hain;
        # AI dono nahi deta, isliye wo pehla nahi, aakhri hai.
        healed = self._heal(key, want)
        if healed:
            return self._to_locator(healed).first

        # Har failure ko kuch sikhana chahiye.
        #
        # Pehle error sirf ye kehta tha ki "nahi mila", aur mujhe har baar
        # alag se dump maangna padta tha. Ab error KHUD bata deta hai ki page
        # pe asli me kaunse field hain -- ek hi run me pata chal jata hai.
        raise LocatorNotFound(
            f"'{key}' page pe nahi mila, aur khud dhoondhne par bhi pakka "
            f"element nahi mila.\n"
            f"  URL: {self.page.url}\n"
            f"  Try kiye: {candidates}\n"
            f"  Aakhri error: {str(last_err)[:120]}\n"
            f"{self._catalogue_hint(key)}\n"
            f"{self.describe_fields()}"
        )

    def _catalogue_hint(self, key: str) -> str:
        from framework import catalogue
        screen = self.current_screen()
        names = catalogue.suggestions(screen, key.split(".")[-1])
        if not names:
            return ""
        return (f"  Catalogue me is screen ({screen}) pe ye naam hain: "
                f"{', '.join(str(n) for n in names[:5])}")

    FIELDS_JS = r"""
    () => {
      const norm = t => (t || '').replace(/\s+/g, ' ').trim();
      const nearLabel = (e) => {
        let box = e.parentElement;
        for (let i = 0; box && i < 3; i++, box = box.parentElement) {
          const l = [...box.querySelectorAll('label, span, td, div')]
            .find(x => x.children.length === 0 && norm(x.innerText).length
                       && norm(x.innerText).length < 30 && !x.contains(e));
          if (l) return norm(l.innerText);
        }
        return '';
      };
      return [...document.querySelectorAll('input, select, textarea')]
        .filter(e => {
          const r = e.getBoundingClientRect();
          return r.width > 0 && r.height > 0 && r.top < innerHeight && r.bottom > 0
                 && !['hidden'].includes(e.type);
        })
        .slice(0, 40)
        .map(e => ({
          tag: e.tagName.toLowerCase(),
          type: e.getAttribute('type') || '',
          id: e.id || '',
          name: e.getAttribute('name') || '',
          fcn: e.getAttribute('formcontrolname') || '',
          ph: e.getAttribute('placeholder') || '',
          label: nearLabel(e),
        }));
    }
    """

    def describe_fields(self) -> str:
        """
        Page pe abhi jo field DIKH rahe hain, unki list -- error me dikhane
        ke liye. Isse locator theek karna ek hi run me ho jata hai.
        """
        try:
            fields = self.page.evaluate(self.FIELDS_JS) or []
        except Exception:  # noqa: BLE001
            return "  (page ke field padhe nahi ja sake)"
        if not fields:
            return "  (screen pe koi field dikh hi nahi raha -- page load hua?)"

        lines = [f"  SCREEN PE YE {len(fields)} FIELD DIKH RAHE HAIN --"
                 f" inme se sahi wala locators file me daal do:"]
        for f in fields:
            bits = [f"<{f['tag']}{'/' + f['type'] if f['type'] else ''}>"]
            for k, lbl in (("id", "id"), ("fcn", "formcontrolname"),
                           ("name", "name"), ("ph", "placeholder"),
                           ("label", "paas ka text")):
                if f[k]:
                    bits.append(f"{lbl}={f[k]!r}")
            lines.append("    " + "  ".join(bits))
        return "\n".join(lines)

    def _heal(self, key: str, want: str = "any") -> str | None:
        """
        AI se locator. Sabse aakhir me, kyunki niyam wale raaste har baar
        ek jaisa natija dete hain aur muft hain -- AI dono nahi deta.
        """
        from framework import heal
        info = heal.heal(self.page, key, want=want)
        if not info:
            return None
        heal.remember(info)
        log.info(f"  [heal] {key} -> {info['selector']}")
        return info["selector"]

    def _metadata_selectors(self, key: str, want: str = "any") -> list[str]:
        """Source scan se nikaale hue raaste (locators/metadata.json)."""
        from framework import code_scanner
        phrase = key.split(".")[-1].replace("_", " ")
        hit = code_scanner.resolve(phrase, kind=want)
        return hit["selectors"] if hit else []

    def _catalogue_selectors(self, key: str, want: str = "any") -> list[str]:
        """Registry se sab raaste -- sabse pakka pehle."""
        from framework import catalogue
        screen = self.current_screen()
        if not screen:
            return []
        phrase = key.split(".")[-1].replace("_", " ")
        hit = catalogue.resolve(screen, phrase, kind=want)
        if not hit:
            return []
        if hit.get("ambiguous"):
            log.warning(f"  [registry] '{phrase}' ke do matlab ho sakte hain "
                        f"({hit['label']} / {hit['others'][:1]}) -- chhod diya")
            return []
        return hit.get("selectors") or [hit["css"]]

    def _from_catalogue(self, key: str, want: str = "any") -> str | None:
        """
        Catalogue se locator. Key ka aakhri hissa hi tester ki bhasha hai:
            'item.name'  -> "name"
            'sale.party' -> "party"
        Screen ka naam page ke URL se nikalta hai.
        """
        from framework import catalogue
        screen = self.current_screen()
        if not screen:
            return None
        phrase = key.split(".")[-1].replace("_", " ")
        hit = catalogue.resolve(screen, phrase, kind=want)
        if not hit:
            return None
        if hit.get("ambiguous"):
            log.warning(f"  [catalogue] '{phrase}' ke do matlab ho sakte hain "
                        f"({hit['label']} / {hit['others'][:1]}) -- chhod diya")
            return None
        return hit["css"]

    def current_screen(self) -> str:
        """
        Abhi kaunsi screen khuli hai -- URL se pehchano.
        Catalogue isi naam se organise hota hai.
        """
        from framework.screens import SCREENS
        url = (self.page.url or "").rstrip("/")
        for name, cfg in SCREENS.items():
            u = cfg.get("url")
            if u and url.endswith(u.rstrip("/")):
                return name
        # form khula ho to uska naam
        tail = url.split("/")[-1] or "unknown"
        return tail.replace("-", "_")

    def remember_screen(self, screen: str | None = None):
        """Is screen ke saare element catalogue me daal do."""
        from framework import catalogue
        return catalogue.capture(self.page, screen or self.current_screen())

    def _learn(self, key: str, want: str = "any") -> str | None:
        """Missing locator ko live page se seekho aur file me likh do."""
        from framework import autolearn
        info = autolearn.learn(self.page, key, want=want)
        if not info:
            return None
        autolearn.remember(info)
        log.info(f"  [autolearn] {key} -> {info['selector']}")
        return info["selector"]

    NEAR_LABEL_JS = r"""
    (label) => {
      const norm = t => (t || '').replace(/\s+/g, ' ').trim().toLowerCase();
      const want = norm(label);

      const visible = (e) => {
        const r = e.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && r.top < innerHeight && r.bottom > 0;
      };

      // 1. asli <label for="..."> ho to sabse achha
      for (const l of document.querySelectorAll('label[for]')) {
        if (norm(l.innerText) === want) {
          const t = document.getElementById(l.getAttribute('for'));
          if (t && visible(t)) { t.setAttribute('data-mb-near', '1'); return true; }
        }
      }
      // 2. label ka text milta ho -> usi dabbe me pehla input
      const leaves = [...document.querySelectorAll('label, span, div, td, th')]
        .filter(e => e.children.length === 0 && e.offsetHeight > 0);
      const hit = leaves.filter(visible).find(e => norm(e.innerText) === want)
               || leaves.filter(visible).find(e => norm(e.innerText).startsWith(want));
      if (!hit) return false;

      // Element SCREEN PAR dikhna chahiye.
      //
      // Bina iske ye Settings panel ka <select id="name"> utha laya tha, jo
      // page me neeche chhupa hua tha. Wahi galti autolearn me bhi hui thi --
      // wahan viewport check laga diya tha, yahan lagana bhool gaya.
      const onScreen = (e) => {
        const r = e.getBoundingClientRect();
        return r.width > 0 && r.height > 0
            && r.bottom > 0 && r.top < innerHeight
            && r.right > 0 && r.left < innerWidth;
      };

      let box = hit.parentElement;
      for (let i = 0; box && i < 4; i++, box = box.parentElement) {
        const all = [...box.querySelectorAll(
          'input:not([type=hidden]):not([type=checkbox]):not([type=radio]), '
          + 'textarea, select')].filter(onScreen);
        if (!all.length) continue;
        // Likhne ke liye <input> chahiye. <select> tabhi jab aur kuch na ho.
        const pick = all.find(e => e.tagName !== 'SELECT') || all[0];
        pick.setAttribute('data-mb-near', '1');
        return true;
      }
      return false;
    }
    """

    def _near_label(self, label: str) -> Locator:
        """Label ke paas wala input. Pehle purana mark hatao, phir naya lagao."""
        self.page.evaluate(
            "() => document.querySelectorAll('[data-mb-near]')"
            ".forEach(e => e.removeAttribute('data-mb-near'))")
        found = self.page.evaluate(self.NEAR_LABEL_JS, label)
        if not found:
            # na mile to aisa selector do jo turant fail ho jaye
            return self.page.locator("[data-mb-near-missing]")
        return self.page.locator("[data-mb-near]")

    def _to_locator(self, sel: str) -> Locator:
        """Support css=, xpath=, text=, role=NAME:label, label=, nearlabel=,
        placeholder=, testid="""
        if sel.startswith("role="):
            body = sel[5:]
            role, _, name = body.partition(":")
            return self.page.get_by_role(role, name=name) if name else self.page.get_by_role(role)
        if sel.startswith("xpath="):
            return self.page.locator(sel)
        if sel.startswith("nearlabel="):
            return self._near_label(sel[10:])
        if sel.startswith("label="):
            return self.page.get_by_label(sel[6:])
        if sel.startswith("placeholder="):
            return self.page.get_by_placeholder(sel[12:])
        if sel.startswith("testid="):
            return self.page.get_by_test_id(sel[7:])
        if sel.startswith("exact_text="):
            return self.page.get_by_text(sel[11:], exact=True)
        return self.page.locator(sel)  # css= / xpath= / plain css

    # ---------- actions ----------

    def goto(self, path: str = "/", check_auth: bool = True):
        url = path if path.startswith("http") else f"{settings.BASE_URL}{path}"
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1200)
        if check_auth:
            safety.check_authorized(self.page, path)

    def settle(self, quiet_ms: int = 500, timeout_ms: int = 15000) -> dict:
        """
        API ka jawab aane tak ruko -- "2 second ruko" ke andaze ki jagah.
        Dheema internet ho to zyada ruk jata hai, tez ho to turant aage.
        """
        from framework import net_wait
        return net_wait.wait_quiet(self.page, quiet_ms, timeout_ms)

    def click(self, key: str):
        el = self.find(key, want="click")
        safety.guarded_click(el, key)
        self.settle()

    def fill(self, key: str, value: str):
        el = self.find(key, want="type")
        safety.guarded_click(el, f"fill:{key}")
        safety.safe_clear(el, self.page)     # fill("") Delete key dabata hai -- mat karo
        if value:
            el.type(str(value), delay=15)    # Marg ke fields keystroke pe lookup firte hain
        self.settle()                        # server ka jawab aane do
        if value:
            try:                              # only a field on the page itself (not one in a popup form) opens a lookup
                in_modal = el.evaluate("e => !!e.closest('ngb-modal-window, .modal')", timeout=1000)
            except Exception:  # noqa: BLE001  (the grid editor closed when the lookup opened)
                in_modal = False
            if not in_modal:
                self._finish_in_lookup(str(value))

    # Typing in a grid's Product / Party cell: the first key opens the Select Item / Select Party window and the
    # rest of the text lands in its search box -- sometimes with the first letters lost while the window opened
    # (TC_SALE_087 typed "QA_Item_GST12", the search box got "Item_G" -> "Not Found!").
    _LOOKUP_SEARCH_JS = """(want) => {
        const box = [...document.querySelectorAll('ngb-modal-window input, .modal.show input')]
            .find(e => e.getClientRects().length && e.type !== 'checkbox' && e.type !== 'radio' && !e.readOnly);
        if (!box) return null;
        return box.value;
    }"""

    def _finish_in_lookup(self, value: str):
        try:
            got = self.page.evaluate(self._LOOKUP_SEARCH_JS, value)
        except Exception:  # noqa: BLE001
            return
        if got is None or got == value or not got or got.lower() not in value.lower():
            return                            # no lookup window, already right, or the user's own other text
        box = self.page.locator("ngb-modal-window input:visible, .modal.show input:visible").first
        try:
            box.focus()
            box.press("Control+a")
            box.type(value, delay=15)
            self.settle()
            print(f"  [fill] the lookup search box had {got!r}: typed the full {value!r}")
        except Exception:  # noqa: BLE001
            pass

    def select(self, key: str, value: str):
        self.find(key).select_option(label=str(value))

    def press(self, key: str, combo: str):
        self.find(key).press(combo)

    def text_of(self, key: str) -> str:
        return (self.find(key).inner_text() or "").strip()

    def is_visible(self, key: str, timeout_ms: int = 4000) -> bool:
        try:
            self.find(key, probe_ms=timeout_ms).wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:  # noqa: BLE001
            return False

    def wait_for_text(self, needle: str, timeout_ms: int | None = None):
        # Any VISIBLE match counts: the app keeps hidden copies of many messages/labels, and `.first` may be one.
        import time as _t
        loc = self.page.get_by_text(needle, exact=False)
        end = _t.time() + (timeout_ms or settings.TIMEOUT) / 1000
        since = self._page_now() - self.TOAST_GRACE_MS
        while True:
            n = min(loc.count(), 30)
            if any(loc.nth(i).is_visible() for i in range(n)):
                return
            if self._toast_seen(needle, since):      # a short-lived message that was shown and already went away
                return
            if _t.time() > end:
                try:                                   # does the page itself contain it? (helps tell tool vs app)
                    inpage = self.page.evaluate("t => (document.body.innerText || '').toLowerCase().includes(t)",
                                                str(needle).lower())
                except Exception:  # noqa: BLE001
                    inpage = None
                hint = " (the page text DOES contain it: the tool could not see it)" if inpage else ""
                raise TimeoutError(f"no visible text {needle!r} after {(timeout_ms or settings.TIMEOUT) // 1000} s{hint}")
            self.page.wait_for_timeout(250)

    def page_has_text(self, needle: str) -> bool:
        if needle.lower() in (self.page.inner_text("body") or "").lower():
            return True
        return self._toast_seen(needle, self._page_now() - self.TOAST_GRACE_MS)

    # A toast (e.g. "Item Is Banned For Selected Party") stays ~3 s. In Test Studio every step also takes a
    # screenshot, so by the next step it can be gone although the app showed it (run R-0026). Messages are
    # recorded as they appear (safety.TOAST_JS); one shown in the last 15 s counts as seen.
    TOAST_GRACE_MS = 15000

    def _page_now(self) -> float:
        try:
            return float(self.page.evaluate("Date.now()"))
        except Exception:  # noqa: BLE001
            return 0.0

    def _toast_seen(self, needle: str, since_ms: float) -> bool:
        try:
            toasts = self.page.evaluate("() => window.__mbToasts || []")
        except Exception:  # noqa: BLE001
            return False
        n = " ".join(str(needle).lower().split())
        return any(n in str(t.get("t", "")).lower() and float(t.get("at", 0)) >= since_ms for t in toasts)

    def screenshot(self, name: str):
        """
        Screenshot lo -- par ye kabhi run ko na giraye.

        MargBooks ke page bahut lambe hote hain (virtual scroll), isliye
        full_page capture kabhi-kabhi timeout ho jata hai. Screenshot ek
        saboot hai, kaam nahi -- fail ho to bas chhod do aage badho.
        """
        settings.ARTIFACTS.mkdir(parents=True, exist_ok=True)
        p = settings.ARTIFACTS / f"{name}.png"

        # 1. poora page (chhota timeout)
        try:
            self.page.screenshot(path=str(p), full_page=True, timeout=5000)
            return p
        except Exception:  # noqa: BLE001
            pass
        # 2. sirf jo screen pe dikh raha hai
        try:
            self.page.screenshot(path=str(p), timeout=4000)
            return p
        except Exception as e:  # noqa: BLE001
            log.warning(f"  [screenshot] '{name}' nahi liya ja saka: {str(e)[:80]}")
            return None
