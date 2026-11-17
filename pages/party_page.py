"""Ledger / Party Master (list) ka page object."""
from __future__ import annotations

from framework import safety
from framework.base_page import BasePage
from framework.screens import open_screen
from pages.grid import (visible_rows, total_count, scroll_all,
                        has_not_found_alert, visible_alerts)


class PartyPage:
    SCREEN = "party"

    def __init__(self, bp: BasePage):
        self.bp = bp
        self.page = bp.page

    @classmethod
    def open(cls, bp: BasePage, verbose: bool = False) -> "PartyPage":
        if not open_screen(bp, cls.SCREEN, verbose=verbose):
            raise RuntimeError(f"Ledger Master khul nahi paya. URL: {bp.page.url}")
        page = cls(bp)
        # Pichhle run ka search filter yaad reh sakta hai -- isliye khali list
        # dikhti thi aur "0 items" wale jhoothe fail aate the.
        try:
            page.clear_search()
        except Exception:  # noqa: BLE001
            pass
        return page

    def search(self, text: str):
        # NOTE: is page ka search #SearchBox hai. Sidebar ka global search bhi
        # name="SearchBox" rakhta hai -- isliye id se hi pakadna zaroori hai.
        el = self.page.locator(self.SEARCH_SEL)
        safety.assert_safe(el, "party.search")
        safety.audit_click(el, "party.search")
        # Har search se pehle raasta saaf: koi popup khula ho to hatao.
        # Warna click "modal intercepts pointer events" pe 15s atak jata hai.
        safety.dismiss_modal(self.page)
        safety.guarded_click(el, "party.search")
        safety.safe_clear(el, self.page)     # fill("") Delete key dabata hai
        if text:
            el.type(text, delay=50)
        # Fixed 1800ms ki jagah: server ka jawab aane tak ruko. Search ka natija
        # API se aata hai -- pehle padhne par purani list milti thi.
        self.bp.settle()
        return self

    def clear_search(self, wait_ms: int = 8000):
        """
        Filter hatao aur rows WAPAS AANE TAK ruko.

        Do baat: (1) turant padhne par khali list milti thi, (2) kabhi-kabhi
        khali karne se app filter dobara nahi chalata, isliye ek harmless
        keystroke (space -> backspace nahi, sirf space aur phir clear) se
        use jaga dete hain.
        """
        self.search("")
        waited = 0
        while waited < wait_ms:
            if self.names():
                return self
            self.bp.settle(quiet_ms=300, timeout_ms=2000)
            waited += 400

        # abhi bhi khali -> filter jaga do: space type karo, phir clear
        try:
            el = self.page.locator(self.SEARCH_SEL)
            el.type(" ", delay=40)
            self.bp.settle()
            safety.safe_clear(el, self.page)
            self.bp.settle()
        except Exception:  # noqa: BLE001
            pass
        return self

    def set_search_by(self, option: str):
        """Name / Mobile / D.L. No. / Address / GSTIN"""
        self.page.locator("#mrgSearchBox").select_option(label=option)
        self.bp.settle()          # dropdown badalne pe bhi server call jaati hai
        return self

    SEARCH_SEL = "input#SearchBox"
    HEADER = "Ledger Name"
    TOTAL_LABEL = "Total No of Ledgers"

    def rows(self) -> list[list[str]]:
        """Abhi dikh rahi rows (virtual scroll -- poori list nahi)."""
        return visible_rows(self.page, self.HEADER)

    def all_rows(self) -> list[list[str]]:
        return scroll_all(self.page, self.HEADER)

    def total(self) -> int | None:
        """
        Header ka total. DHYAAN: ye poore database ka total hai, filter ke
        saath NAHI badalta. Filter check karne ke liye filter_works().
        """
        return total_count(self.page, self.TOTAL_LABEL)

    def names(self) -> list[str]:
        return [r[0] for r in self.rows() if r and r[0]]

    def row_count(self) -> int:
        return len(self.names())

    def total_count(self) -> int | None:
        return self.total()

    def filter_works(self, term: str) -> dict:
        """
        Search sach me filter kar raha hai? Iska sahi paimana ye hai ki
        DIKH RAHI har row me search ka shabd ho -- ginti nahi, kyunki
        header ka total filter pe badalta hi nahi aur virtual scroll ki
        wajah se rows ki ginti bharosemand nahi.
        """
        rows = self.names()
        matching = [n for n in rows if term.lower() in n.lower()]
        return {
            "shown": len(rows),
            "matching": len(matching),
            "all_match": len(rows) > 0 and len(matching) == len(rows),
            "sample": rows[:3],
        }

    def search_check(self, term: str) -> dict:
        """
        Search ka poora imtihan -- search KARNE SE PEHLE ki haalat ke saath tulna.

        MargBooks me search ke teen sahi vyavhaar hain:
          FILTER    : rows chhoti ho gayin, jo bachi wo sab match karti hain
          FILTER-0  : kuch match nahi hua to list KHALI ho gayi (pehle rows thin)
          JUMP      : rows waisi hi, par matching record sabse UPAR aa gaya
          NOT_FOUND : app ne khud alert dikhaya "record not found"

        Sirf ek soorat bug hai:
          SILENT    : list bilkul waisi hi, match bhi nahi, aur koi message bhi
                      nahi. User ko lagega app ne kuch kiya hi nahi.

        Pichhli galti: maine "0 rows" ko bhi silent maan liya tha, jabki wo
        filter ka sahi natija tha -- kyunki maine PEHLE ki ginti se tulna
        hi nahi ki thi.
        """
        from framework import safety

        before = self.names()
        try:
            t0 = self.page.evaluate("() => Date.now()")
        except Exception:  # noqa: BLE001
            t0 = 0

        self.search(term)
        after = self.names()
        t = term.lower()
        matching = [n for n in after if t in n.lower()]

        # "Not found" do jagah ho sakta hai, aur dono dekhni padti hain:
        #   1. INLINE -- MargBooks isse search bar ke NEECHE dikhata hai
        #      (Item aur Ledger dono me). Ye toast nahi hai.
        #   2. TOAST  -- jo do second me gayab ho jata hai, isliye recorder se.
        alert_msg = ""
        try:
            from pages.grid import has_not_found_alert, NOT_FOUND_WORDS
            found, msg = has_not_found_alert(self.page)      # inline
            if found:
                alert_msg = msg
            else:
                for tt in safety.get_toasts(self.page):      # toast
                    if tt.get("at", 0) >= t0 and any(
                            w in tt.get("t", "").lower() for w in NOT_FOUND_WORDS):
                        alert_msg = tt["t"]
                        break
        except Exception:  # noqa: BLE001
            pass

        if alert_msg:
            mode = "not_found"
        elif after and len(matching) == len(after):
            mode = "filter"
        elif not after and before:
            mode = "filter_empty"          # sab filter ho gaya, kuch match nahi
        elif after and t in after[0].lower():
            mode = "jump"
        else:
            mode = "silent"                # <- yahi asli bug hai

        return {
            "mode": mode,
            "works": mode != "silent",
            "before": len(before),
            "after": len(after),
            "matching": len(matching),
            "first": after[0] if after else None,
            "alert": alert_msg,
        }

    # purana naam chalta rahe
    def search_result(self, term: str) -> dict:
        return self.search_check(term)

    def has(self, name: str) -> bool:
        """Abhi DIKH rahi rows me hai ya nahi. Poori list me dhoondhna ho to
        pehle search() karo -- warna virtual scroll ki wajah se miss ho sakta hai."""
        return any(name.lower() in n.lower() for n in self.names())

    def open_create(self):
        btn = self.page.get_by_role("button", name="Create/F2").first
        safety.guarded_click(btn, "party.create")
        self.bp.settle()
        safety.dismiss_modal(self.page)
        return self
