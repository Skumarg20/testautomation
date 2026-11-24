"""
Har screen tak pahunchne ka rasta -- dump_menus.txt se banaya gaya.

MargBooks ke submenu ka koi asli URL nahi hai (sab javascript:void(0)),
isliye click hi ekmatr rasta hai. Jahan URL kaam karta hai wahan wo pehle
try hota hai kyunki tez hai; na chale to menu se click.
"""
from __future__ import annotations

from framework.base_page import BasePage
from framework import nav
from framework.safety import check_authorized

SCREENS: dict[str, dict] = {
    # ---- Masters ----
    "item":        {"url": "/item-master/list", "marker": "Item List",
                    "menu": "master", "path": ["Inventory Master", "Item"]},
    # Create form alag PAGE hai -- list se Create/F2 dabane par khulta hai.
    # Iska naksha kabhi bana hi nahi tha, isliye saare create test fail the.
    "item_create": {"url": "/item-master/item-create",
                    "marker": ["Create Item", "Product", "Description", "M.R.P"],
                    "menu": "master", "path": ["Inventory Master", "Item"],
                    "after_create": True},
    "party":       {"url": "/partymaster/list", "marker": "Ledger Master",
                    "menu": "master", "path": ["Accounts Master", "Ledger"]},
    "party_create": {"url": "/partymaster/action/create",
                     "marker": ["Create Party", "Party Name", "Ledger Name", "Create Ledger"],
                     "menu": "master", "path": ["Accounts Master", "Ledger"],
                     "after_create": True},
    "group":       {"url": None, "marker": "Group",
                    "menu": "master", "path": ["Accounts Master", "Group"]},
    "store":       {"url": None, "marker": "Store",
                    "menu": "master", "path": ["Inventory Master", "Store"]},
    "agency":      {"url": None, "marker": "Agency",
                    "menu": "master", "path": ["Inventory Master", "Agency"]},
    "salt":        {"url": None, "marker": "Salt",
                    "menu": "master", "path": ["Inventory Master", "Salt"]},
    "hsn":         {"url": None, "marker": "HSN",
                    "menu": "master", "path": ["Inventory Master", "HSN/SAC"]},
    "unit":        {"url": None, "marker": "Unit",
                    "menu": "master", "path": ["Inventory Master", "Unit"]},
    "price_list":  {"url": None, "marker": "Price",
                    "menu": "master", "path": ["Rate Master", "Price List"]},
    "opening_stock": {"url": None, "marker": "Stock",
                    "menu": "master", "path": ["Opening Balance", "Stock"]},

    # ---- Sale ----
    # Label pe click = LIST | "+" pe click = NAYA form  (plus: True)
    "sale_list":        {"marker": ["Sale Bill List"], "menu": "sale", "path": ["Bill"]},
    "sale_bill":        {"marker": ["Party Name"], "menu": "sale", "path": ["Bill"], "plus": True, "tab": "Sale Bill"},
    "sale_challan":     {"marker": ["Party Name", "Challan"], "menu": "sale", "path": ["Challan"], "plus": True},
    "sale_pos":         {"marker": ["POS", "Party Name"], "menu": "sale", "path": ["POS"]},
    "sale_quotation":   {"marker": ["Party Name", "Quotation"], "menu": "sale", "path": ["Quotation"], "plus": True},
    "counter_sale":     {"marker": ["Counter", "Party Name"], "menu": "sale", "path": ["Counter Sale"]},
    "sale_stock_issue": {"marker": ["Stock Issue", "Party Name"], "menu": "sale", "path": ["Stock Issue"], "plus": True},
    "sale_order":       {"marker": ["Party Name", "Order"], "menu": "sale", "path": ["Order"], "plus": True},
    "sale_return":      {"marker": ["Party Name", "Return"], "menu": "sale", "path": ["Return"], "plus": True,
                         "tab": "Sale Return"},
    "sale_return_challan": {"marker": ["Party Name", "Return"], "menu": "sale", "path": ["Return Challan"], "plus": True},
    "sale_draft":       {"marker": ["Draft"], "menu": "sale", "path": ["Draft"]},
    "sale_pd_cn":       {"marker": ["Party Name"], "menu": "sale", "path": ["Price Diff.Sale C/N"], "plus": True},
    "sale_pd_dn":       {"marker": ["Party Name"], "menu": "sale", "path": ["Price Diff.Sale D/N"], "plus": True},

    # ---- Purchase ----
    "purchase_list":       {"url": "/purchase/purchasebook/bill", "marker": ["Purchase Bill List", "Bill No"], "menu": "purchase", "path": ["Bill"]},
    "purchase_bill":       {"marker": ["Party Name"], "menu": "purchase", "path": ["Bill"], "plus": True},
    "purchase_challan":    {"marker": ["Party Name", "Challan"], "menu": "purchase", "path": ["Challan"], "plus": True},
    "purchase_quotation":  {"marker": ["Party Name", "Quotation"], "menu": "purchase", "path": ["Quotation"], "plus": True},
    "purchase_stock_recv": {"marker": ["Party Name", "Stock Receive"], "menu": "purchase", "path": ["Stock Receive"], "plus": True},
    "purchase_order":      {"marker": ["Party Name", "Order"], "menu": "purchase", "path": ["Order"], "plus": True},
    "purchase_return":     {"marker": ["Party Name", "Return"], "menu": "purchase", "path": ["Return"], "plus": True},
    "purchase_return_challan": {"marker": ["Party Name", "Return"], "menu": "purchase", "path": ["Return Challan"], "plus": True},
    "purchase_brk_exp":    {"marker": ["Brk", "Party Name"], "menu": "purchase", "path": ["Brk/Exp Issue"], "plus": True},
    "purchase_pd_cn":      {"marker": ["Party Name"], "menu": "purchase", "path": ["Price Diff.Pur C/N"], "plus": True},
    "purchase_pd_dn":      {"marker": ["Party Name"], "menu": "purchase", "path": ["Price Diff.Pur D/N"], "plus": True},
    "purchase_draft":      {"marker": ["Draft", "purchase draft"], "menu": "purchase", "path": ["purchase draft"]},

    # ---- Accounting ----
    "receipt":     {"url": "/transaction/voucher/receipt/53", "marker": "Receipt",
                    "menu": "accounting", "path": ["Receipt"]},
    "payment":     {"url": "/transaction/voucher/payment/51", "marker": "Payment",
                    "menu": "accounting", "path": ["Payment"]},
    "credit_note": {"url": "/transaction/voucher/creditnote/57", "marker": "Credit Note",
                    "menu": "accounting", "path": ["Credit Note"]},
    "debit_note":  {"url": "/transaction/voucher/debitnote/56", "marker": "Debit Note",
                    "menu": "accounting", "path": ["Debit Note"]},
    "journal":     {"url": "/transaction/voucher/journal/58", "marker": "Journal",
                    "menu": "accounting", "path": ["Journal"]},

    # ---- Stock ----
    "stock_transfer": {"url": None, "marker": "Transfer",
                       "menu": "stock", "path": ["Stock Transfer"]},
    "physical_stock": {"url": None, "marker": "Physical",
                       "menu": "stock", "path": ["Physical Stock"]},

    # ---- Seedhe sidebar links (inka koi dropdown nahi hai) ----
    "dashboard":   {"url": "/dashboard", "marker": ["Last Sync", "Net Sale", "Getting Started"],
                    "nav": "dashboard"},
    "report":      {"marker": ["Report"], "nav": "report"},
    "utilities":   {"url": "/mb/utillity-menu", "marker": ["Utilities & Tools"], "nav": "utilities"},
}


def _form_is_empty(bp: BasePage) -> bool:
    """Khula transaction form khali hai? (koi line nahi jodi gayi)"""
    try:
        return bp.page.evaluate(r"""
          () => {
            const rows = [...document.querySelectorAll('table tbody tr')]
              .filter(r => (r.innerText || '').trim().length > 3);
            return rows.length === 0;
          }
        """)
    except Exception:  # noqa: BLE001
        return False


def _close_open_form(bp: BasePage):
    """Bhara hua form band karo -- bina save kiye."""
    from framework import safety
    try:
        btn = bp.page.locator('button[id^="btnEsc"]').first
        if btn.is_visible(timeout=1500):
            safety.guarded_click(btn, "form.close", timeout=3000)
            bp.page.wait_for_timeout(900)
            safety.dismiss_modal(bp.page)
            bp.page.wait_for_timeout(600)
    except Exception:  # noqa: BLE001
        pass


# Screen key -> MargBooks keyboard shortcut (from the dashboard or an empty form).
SHORTCUTS = {"sale_bill": "Alt+N", "sale_list": "Alt+M", "sale_challan": "Alt+C", "counter_sale": "Alt+A",
             "purchase_bill": "Alt+P", "item": "Alt+I", "sale_stock_issue": "Alt+K", "dashboard": "Alt+H"}


def open_screen(bp: BasePage, key: str, verbose: bool = False,
                prefer: str = "menu") -> bool:
    """
    Screen kholo.

    prefer="menu" (default) -> menu se jao, jaise asli user jata hai.
                     URL se jaane par POORA PAGE RELOAD hota hai: app dobara
                     load hoti hai, sab dheema hota hai, aur wo raasta asli
                     user kabhi leta bhi nahi. Isliye menu hi default hai.
    prefer="url"  -> seedha URL. Sirf tab jab menu toota ho aur kaam nikaalna ho.
    """
    cfg = SCREENS.get(key)
    if not cfg:
        raise KeyError(f"'{key}' screens.py me nahi hai. Available: {sorted(SCREENS)}")

    markers = cfg["marker"]
    if isinstance(markers, str):
        markers = [markers]

    def url_ok() -> bool:
        """
        URL bhi wahi hai jahan hona chahiye?

        ASLI BUG: 'item' screen ka marker text dashboard par bhi mil gaya,
        aur open_screen ne "khul gaya" keh diya -- jabki hum dashboard par
        hi khade the. Uske baad har cheez wahan dhoondhi gayi jo thi hi
        nahi, aur error kehta raha "field nahi mila".

        Text jhooth bol sakta hai (chhupe panel, menu, dashboard ke tile).
        URL nahi bolta.
        """
        want = (cfg.get("url") or "").rstrip("/")
        if not want:
            # No pinned URL: at least we must have left the dashboard (its tiles carry most screen names,
            # so the text check alone said "open" while nothing had moved).
            return key == "dashboard" or not (bp.page.url or "").split("?")[0].rstrip("/").endswith("/dashboard")
        here = (bp.page.url or "").rstrip("/")
        return here.endswith(want)

    def tab_ok() -> bool:
        """Forms open as tabs ("Sale Bill 1", "Sale Return Credit Note 1"). A Sale Bill also says "Party Name",
        so text alone took a Sale Bill for a Sale Return (Billing General): the ACTIVE tab must match too."""
        want = cfg.get("tab")
        if not want:
            return True
        try:
            titles = bp.page.evaluate("""() => [...document.querySelectorAll('li.active > a, .nav-tabs .active')]
                .filter(a => a.getClientRects().length).map(a => (a.innerText || '').trim())""")
        except Exception:  # noqa: BLE001
            return True
        titles = [t for t in titles if t and not t.lower().startswith(("notification", "announcement"))]
        if not titles:                      # no form tabs in this layout: nothing to compare
            return True
        return any(t.lower().startswith(want.lower()) for t in titles)

    def seen() -> bool:
        """Screen sach me khuli hai? Text AUR URL, dono."""
        text_ok = any(bp.page_has_text(m) for m in markers)
        if not text_ok:
            return False
        if not tab_ok():
            if verbose:
                print(f"   '{key}' ka text mila par khula tab '{cfg.get('tab')}' nahi hai")
            return False
        if not url_ok():
            if verbose:
                print(f"   '{key}' ka text to mila, par URL galat hai "
                      f"({bp.page.url}) -- khula nahi maana")
            return False
        return True

    def remember():
        """
        Screen khulte hi uske saare element yaad kar lo.
        Testing ke SAATH-SAATH agent apna gyaan badhata rahe -- yahi asli baat
        hai. Agli baar us screen ka koi bhi field bina bataye mil jayega.
        """
        import os
        if os.environ.get("MB_NO_CAPTURE"):     # parallel sessions: never write the shared registry at once
            return
        try:
            from framework import catalogue
            catalogue.capture(bp.page, key, verbose=verbose)
        except Exception:  # noqa: BLE001
            pass

    # Pehle se yahin hain? To kuch mat karo -- na click, na reload.
    #
    # Ye create-form (plus) ke liye BHI lagu hota hai. Pehle maine unhe chhod
    # diya tha, aur natija ye hua ki har test ek NAYA bill tab khol deta tha
    # (suffix 42, 50, 67, 87...). Tabs jama hote gaye, app dheema hota gaya,
    # aur "har baar refresh ho raha hai" wali shikayat isi se thi.
    #
    # Khula form KHALI ho tabhi dobara use karte hain -- warna pichhle test ka
    # bhara hua data agle test me mil jayega.
    if seen():
        if not cfg.get("plus") or _form_is_empty(bp):
            if verbose:
                print(f"   pehle se '{key}' khula hai -- wahi use kar rahe hain")
            remember()
            return True
        if verbose:
            print(f"   '{key}' khula hai par usme data hai -- band karke naya kholenge")
        _close_open_form(bp)

    def open_create() -> bool:
        """List page pe pahunch gaye -- ab Create/F2 dabao."""
        for label in ("Create/F2", "Create", "New", "Add New"):
            try:
                if nav.click_submenu(bp, label):
                    bp.page.wait_for_timeout(2500)
                    check_authorized(bp.page, key)
                    if seen():
                        if verbose:
                            print(f"   '{label}' se form khul gaya")
                        return True
            except Exception:  # noqa: BLE001
                continue
        return seen()

    # MargBooks' own keyboard shortcuts (Alt+N new sale bill, Alt+M sale list, Alt+P purchase bill...) are what a
    # user presses and, unlike the side menu, work whether the menu is collapsed or expanded. The live-app checks
    # (artifacts/verify) found the menu route for sale_bill hanging for minutes while Alt+N opened it every time.
    keys = SHORTCUTS.get(key)
    if keys and prefer != "url":
        try:
            # leave a focused text box without clicking anything (a click could land on a button)
            bp.page.evaluate("() => { const e = document.activeElement; if (e && /INPUT|TEXTAREA/.test(e.tagName)) e.blur(); }")
        except Exception:  # noqa: BLE001
            pass
        for _ in range(2):
            try:
                bp.page.keyboard.press(keys)
                bp.page.wait_for_timeout(3500)
                check_authorized(bp.page, key)
                if seen():
                    if verbose:
                        print(f"   '{key}' {keys} se khul gaya")
                    remember()
                    return True
            except Exception as e:  # noqa: BLE001
                from framework.safety import ModuleNotEnabled
                if isinstance(e, ModuleNotEnabled):
                    raise
                if verbose:
                    print(f"   {keys} se nahi khula: {str(e)[:80]}")

    if cfg.get("url") and prefer != "menu":
        bp.goto(cfg["url"], check_auth=False)
        bp.page.wait_for_timeout(2500)
        check_authorized(bp.page, key)
        if seen():
            return True
        if verbose:
            print(f"   URL se nahi khula, menu se try kar rahe hain...")

    # Seedha sidebar link -- dropdown kholne ki zaroorat nahi
    if cfg.get("nav"):
        try:
            bp.click(f"nav.{cfg['nav']}")
            bp.page.wait_for_timeout(2500)
            check_authorized(bp.page, key)
            return seen()
        except Exception as e:  # noqa: BLE001
            if verbose:
                print(f"   sidebar link '{cfg['nav']}' fail: {str(e)[:80]}")
            return False

    menu, path = cfg.get("menu"), cfg.get("path") or []
    want_new = bool(cfg.get("plus"))
    if not menu:
        return False

    try:
        nav.open_menu(bp, menu)

        # Naya banana hai -> seedha us row ke "+" pe click.
        if want_new and path:
            for sec in path[:-1]:
                nav.ensure_expanded(bp, sec)
            label = path[-1]
            # "+" kabhi-kabhi pehli baar nahi lagta (menu animation), isliye
            # do koshish. purchase_bill isi wajah se fail ho raha tha.
            clicked = nav.click_submenu_plus(bp, label)
            if not clicked:
                nav.open_menu(bp, menu)
                bp.page.wait_for_timeout(700)
                clicked = nav.click_submenu_plus(bp, label)
            if clicked:
                bp.page.wait_for_timeout(2000)
                check_authorized(bp.page, key)
                if seen():
                    if verbose:
                        print(f"   '{label}' ke + se naya form khul gaya")
                    remember()
                    return True
            if verbose:
                print(f"   '+' nahi mila, list se Create/F2 try karenge...")
            nav.open_menu(bp, menu)

        # path ka aakhri item = asli screen ka link
        # usse pehle ke items = accordion sections -> sirf EXPAND karo, toggle nahi
        for label in path[:-1]:
            if not nav.ensure_expanded(bp, label):
                if verbose:
                    print(f"   section '{label}' khul nahi paya")
                return False

        if not nav.click_submenu(bp, path[-1]):
            if verbose:
                print(f"   '{path[-1]}' pe click nahi ho paya")
            return False
        bp.page.wait_for_timeout(1800)

        bp.page.wait_for_timeout(2000)
        check_authorized(bp.page, key)
        if seen() and not want_new:
            remember()
            return True
        if want_new:
            ok = open_create()
            if ok:
                remember()
            return ok
        if seen():
            remember()
            return True

        # menu se nahi khula. URL hai to bata do ki MENU toota hai, URL nahi.
        if cfg.get("url") and prefer == "menu":
            bp.goto(cfg["url"], check_auth=False)
            bp.page.wait_for_timeout(2000)
            if seen() and verbose:
                print(f"   NOTE: menu se nahi khula par URL se khul gaya "
                      f"-> menu ka rasta toota hai")
        return False
    except Exception as e:  # noqa: BLE001
        from framework.safety import ModuleNotEnabled
        if isinstance(e, ModuleNotEnabled):
            raise
        if verbose:
            print(f"   menu nav error: {e}")
        return False
