"""
Menu se navigate karna.

MargBooks ke kuch screens ka apna URL nahi hai (Sale Bill /transaction pe jaao
to dashboard pe fenk deta hai). Wo sirf left menu se khulte hain:
    Sale (menu) -> submenu -> Sale Bill

Yahan dono raaste hain: pehle seedha URL, na chale to menu se click.
"""
from __future__ import annotations

from framework.base_page import BasePage
from config.settings import settings


def section_state(bp: BasePage, label: str) -> str:
    """
    Accordion section khula hai ya band -- 'open' | 'closed' | 'notfound'.

    Ye jaanna zaroori hai kyunki menu TOGGLE karta hai: khule hue section pe
    click karoge to wo BAND ho jayega. Pehle robot har baar click kar deta tha,
    isliye ek chhodkar ek screen fail ho rahi thi.
    """
    try:
        return bp.page.evaluate(
            r"""
            (label) => {
              const norm = t => (t || '').replace(/\s+/g, ' ').trim();
              const nodes = [...document.querySelectorAll('a, button, div, span')];
              const node = nodes.find(e => norm(e.innerText).startsWith(label)
                                        && norm(e.innerText).length < label.length + 25);
              if (!node) return 'notfound';

              const aria = node.getAttribute('aria-expanded');
              if (aria === 'true') return 'open';
              if (aria === 'false') return 'closed';

              const cls = (typeof node.className === 'string' ? node.className : '');
              if (/\bcollapsed\b/.test(cls)) return 'closed';
              if (/\bshow\b|\bopen\b|\bactive\b/.test(cls)) return 'open';

              // panel bhai-bandhu dekh lo
              let sib = node.nextElementSibling;
              for (let i = 0; sib && i < 3; i++, sib = sib.nextElementSibling) {
                const c = (typeof sib.className === 'string' ? sib.className : '');
                if (/collapse|submenu|dropdown-menu|nav/i.test(c)) {
                  const vis = sib.offsetHeight > 0 && getComputedStyle(sib).display !== 'none';
                  return vis ? 'open' : 'closed';
                }
              }
              return 'closed';
            }
            """,
            label,
        )
    except Exception:  # noqa: BLE001
        return "notfound"


def ensure_expanded(bp: BasePage, label: str) -> bool:
    """
    Section ko KHULA karo. Pehle se khula ho to haath mat lagao.
    Ye poore navigation ka sabse zaroori niyam hai.
    """
    st = section_state(bp, label)
    if st == "open":
        return True
    if not click_submenu(bp, label):
        return False
    bp.page.wait_for_timeout(900)
    return section_state(bp, label) != "closed"


def open_menu(bp: BasePage, menu_key: str):
    """
    Left sidebar ka dropdown menu kholo -- agar pehle se khula ho to chhod do,
    warna click karne se wo band ho jayega.
    """
    from framework.locator_store import store as _store
    label_map = {
        "master": "Master", "sale": "Sale", "purchase": "Purchase",
        "accounting": "Accounting Trans.", "stock": "Stock Management",
        "banking": "Banking", "crm": "CRM",
    }
    label = label_map.get(menu_key, menu_key.title())

    if section_state(bp, label) == "open":
        bp.page.wait_for_timeout(300)
        return
    bp.click(f"nav.{menu_key}")
    bp.page.wait_for_timeout(900)


def submenu_links(bp: BasePage) -> list[tuple[str, str]]:
    """Abhi khule hue menu ke andar ke (text, href) nikaalo."""
    return bp.page.evaluate("""
      () => [...document.querySelectorAll('.collapse.show a, .show > a, ul.show a, li.open a')]
        .map(a => [ (a.innerText||'').trim(), a.getAttribute('href')||'' ])
        .filter(([t]) => t && t.length < 60)
    """)


def click_submenu(bp: BasePage, label: str) -> bool:
    """
    Khule menu ya page me se ek item pe click karo.
    "+" jaise chhote label ke liye button/icon bhi try karta hai.
    """
    from framework import safety

    attempts = [
        lambda: bp.page.get_by_role("link", name=label, exact=True).first,
        lambda: bp.page.get_by_role("button", name=label, exact=True).first,
        lambda: bp.page.get_by_role("link", name=label).first,
        lambda: bp.page.get_by_role("button", name=label).first,
    ]
    if len(label) > 2:      # "+" ke liye has_text bahut dhila pad jata hai
        attempts += [
            lambda: bp.page.locator("button", has_text=label).first,
            lambda: bp.page.locator("a", has_text=label).first,
        ]
    else:
        attempts += [
            lambda: bp.page.locator(f'button:text-is("{label}")').first,
            lambda: bp.page.locator(f'a:text-is("{label}")').first,
        ]

    for attempt in attempts:
        try:
            loc = attempt()
            loc.wait_for(state="visible", timeout=3000)
            safety.guarded_click(loc, f"submenu:{label}")
            bp.page.wait_for_timeout(2500)
            return True
        except Exception:  # noqa: BLE001
            continue
    return False


def goto(bp: BasePage, url_path: str | None, marker: str,
         menu: str | None = None, submenu: str | None = None) -> bool:
    """
    Ek screen tak pahuncho.
      1. url_path try karo (agar diya hai)
      2. marker na mile to menu -> submenu se jao
    marker mila to True.
    """
    page = bp.page

    if url_path:
        bp.goto(url_path)
        page.wait_for_timeout(2500)
        if bp.page_has_text(marker):
            return True

    if menu and submenu:
        try:
            open_menu(bp, menu)
            if click_submenu(bp, submenu):
                page.wait_for_timeout(2500)
                if bp.page_has_text(marker):
                    return True
        except Exception:  # noqa: BLE001
            pass

    return False


def click_submenu_plus(bp: BasePage, label: str) -> bool:
    """
    Submenu row ke DAAYIN taraf wale "+" icon pe click karo.

    MargBooks me har transaction row aisi hai:
        [ Bill                    + ]
    Label pe click = LIST khulti hai.
    "+" pe click   = NAYA banane ka form khulta hai.

    "+" akela dhoondhna bekaar hai (page pe kai hote hain), isliye hum pehle
    label wali row dhoondhte hain, phir usi row ke andar ka "+" uthate hain.
    """
    from framework import safety

    handle = bp.page.evaluate_handle(
        r"""
        (label) => {
          const norm = t => (t || '').replace(/\s+/g, ' ').trim();
          const nodes = [...document.querySelectorAll('a, span, li, div')];
          const node = nodes.find(e => norm(e.innerText) === label
                                     && e.children.length <= 2);
          if (!node) return null;

          // SIRF ISI ROW ke andar dhoondho -- upar CHADHNA nahi.
          //
          // ASLI BUG: pehle ye 3 parat upar chadhta tha. Group ki row me
          // "+" nahi hai, to wo upar jaakar LEDGER ka "+" utha laya --
          // aur Group ka create maang kar Ledger ka form khul gaya.
          //
          // Crawler use "Group ka create form" likh deta. Ye sabse bura
          // tarah ka bug hai: galat data, jo galat lagta bhi nahi.
          //
          // Jis row me "+" nahi hai, uska matlab hai wahan "+" hai hi
          // nahi. Us soorat me khali haath lautna sahi hai -- crawler
          // phir list ke "Create" button se kaam chala lega.
          const row = node.closest('li, tr, .menu-item, .nav-item')
                      || node.parentElement;
          if (!row) return null;

          const plus = [...row.querySelectorAll('a, span, i, button, svg')]
            .find(e => norm(e.innerText) === '+'
                    || /(^|[-_ ])(plus|add|new)([-_ ]|$)/i.test(e.className || '')
                    || /plus|add/i.test(e.getAttribute('title') || ''));
          if (!plus) return null;

          // Dohri jaanch: jo "+" mila, uski apni row wahi honi chahiye
          // jisme label hai. Nested list me ye bacha leta hai.
          const plusRow = plus.closest('li, tr, .menu-item, .nav-item');
          if (plusRow && plusRow !== row) return null;
          return plus;
        }
        """,
        label,
    )
    el = handle.as_element()
    if not el:
        return False
    try:
        el.scroll_into_view_if_needed()
        safety.guarded_click(el, f"plus:{label}")
        bp.page.wait_for_timeout(2500)
        return True
    except Exception:  # noqa: BLE001
        return False
