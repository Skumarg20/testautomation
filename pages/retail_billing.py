"""
Retail Billing / Counter Sale -- jo bill counter par kata jata hai.

KYUN ISKA APNA HISSA HAI
------------------------
Retail bill ka rasta Control Room ki ek setting se poori tarah badal jata hai:

    "Ask Party in Retail Billing" = Ask        -> party poochta hai
    "Ask Party in Retail Billing" = Don't Ask  -> party poochta hi nahi,
                                                  Cash Account apne aap lagta hai

Chemist trade me aksar "Don't Ask" hota hai -- counter par har grahak ka
ledger nahi banaya jata. Us haalat me party ka intezaar karna matlab test
ka hamesha atakna.

Aur ulta bhi: "Ask" hone par party bhare bina item ka grid khulta hi nahi.

Isliye yahan koi FIXED script nahi hai. Form khulne par PEHLE dekhte hain
ki party ka field hai ya nahi, aur usme kuch pehle se bhara hai ya nahi --
phir usi hisaab se aage badhte hain. Ek hi test dono settings pe chalta hai.
"""
from __future__ import annotations

from framework import control_room, safety
from framework.base_page import BasePage
from framework.page_ready import wait_ready
from pages import ag_grid, form_profile, lookup
from pages.sale_bill_page import SaleBillPage


class RetailBillPage(SaleBillPage):
    SCREEN = "counter_sale"
    TITLE = "Counter Sale"

    # ---- party ka faisla ----

    def party_state(self) -> dict:
        """
        Party ka abhi kya haal hai? Teen soorat ho sakti hain:

            "prefilled"  -> field hai aur usme naam pehle se bhara hai
            "empty"      -> field hai par khali -- pehle bharna padega
            "not_asked"  -> field hai hi nahi (Don't Ask wali setting)

        Faisla SCREEN dekh kar hota hai, setting ka naam maan kar nahi.
        Setting ki apni value bhi padhte hain, par wo sirf batane ke liye --
        kyunki asli sach wahi hai jo form me dikh raha hai.
        """
        prof = self.profile()
        setting = control_room.get("ask_party_retail") or {}

        if not prof.has("party"):
            return {"state": "not_asked", "value": "",
                    "setting": setting.get("value", "?"),
                    "why": "Form me party ka field hai hi nahi"}

        try:
            el = form_profile.field_locator(self.bp, "party")
            value = (el.input_value() or "").strip()
        except Exception:  # noqa: BLE001
            value = ""

        if value:
            return {"state": "prefilled", "value": value,
                    "setting": setting.get("value", "?"),
                    "why": f"Party pehle se bhari hai: {value}"}
        return {"state": "empty", "value": "",
                "setting": setting.get("value", "?"),
                "why": "Party ka field khali hai -- bharna padega"}

    def ensure_party(self, name: str = "Cash Account") -> dict:
        """
        Party ka intezaam karo -- jo bhi haalat ho.

        Pehle se bhari ho ya poochi hi na ja rahi ho, to usse CHHED TE nahi.
        Counter par jo default aata hai wahi asli vyavhaar hai; use badal
        dena test ko us raste se hata dega jo asli user leta hai.
        """
        st = self.party_state()
        if st["state"] in ("prefilled", "not_asked"):
            return {**st, "action": "kuch nahi kiya"}

        el = form_profile.field_locator(self.bp, "party")
        lookup.pick(self.bp, el, name, what="party")
        self.clear_popups()
        return {**self.party_state(), "action": f"'{name}' chuni"}

    # ---- poora bill ----

    def bill(self, item: str, qty: float = 1, rate: float | None = None,
             batch: str | None = None, party: str = "Cash Account",
             patient: str | None = None, doctor: str | None = None,
             save: bool = False) -> dict:
        """
        Ek retail bill banao -- jo jo cheezein is form me hain, wahi bhar kar.

        Wapas deta hai: har kadam par kya hua. Isse report me saaf dikhta hai
        ki kaunsa hissa is company me hai hi nahi (aur isliye chhoda gaya),
        aur kaunsa sach me chala.
        """
        steps: list[str] = []

        p = self.ensure_party(party)
        steps.append(f"party: {p['state']} ({p['why']})")

        # item -- barcode ho to barcode, warna naam
        if str(item).strip().isdigit():
            self.add_by_barcode(str(item).strip(), qty, rate)
            steps.append(f"item: barcode {item} x{qty}")
        else:
            self.add_by_name(item, qty, rate)
            steps.append(f"item: {item} x{qty}")

        # batch sirf tab jab is trade me batch hota hi ho
        prof = self.profile()
        if batch and prof.needs_batch:
            self.pick_batch(batch)
            steps.append(f"batch: {batch}")
        elif batch:
            steps.append("batch: is trade me batch nahi hota -- chhoda")

        # patient / doctor -- pharma me hote hain, general me nahi
        extra = {}
        if patient and prof.has("patient_name"):
            extra["patient_name"] = patient
        if doctor and prof.has("doctor_name"):
            extra["doctor_name"] = doctor
        if extra:
            for key, val in extra.items():
                el = form_profile.field_locator(self.bp, key)
                safety.guarded_click(el, f"retail.{key}")
                safety.safe_clear(el, self.page)
                el.type(str(val), delay=40)
                el.press("Enter")
            steps.append(f"details: {', '.join(extra)}")
        elif patient or doctor:
            steps.append("details: is trade me patient/doctor nahi hote -- chhode")

        lines = ag_grid.line_count(self.page)
        steps.append(f"grid: {lines} line")

        if save:
            self.save()
            steps.append("save: bill save kiya")
        else:
            self.close()
            steps.append("save: nahi kiya, form band kiya")

        return {"trade": prof.trade, "party": p, "lines": lines, "steps": steps}

    # ---- kholna ----

    @classmethod
    def open(cls, bp: BasePage, verbose: bool = False):
        from framework.screens import open_screen
        if not open_screen(bp, cls.SCREEN, verbose=verbose):
            raise RuntimeError(f"'{cls.SCREEN}' khul nahi paya")
        wait_ready(bp.page, timeout_ms=20000)
        page = cls(bp)
        page.clear_popups()
        page.refresh()
        return page
