"""
Har transaction form (Sale Bill, Purchase Bill, Return, Challan...) ka base.

SABSE ZAROORI BAAT -- badalta hua ID suffix:
    Sale Bill   me field hai  txtLedgerName27, btnSave27, btnEsc27
    Sale Return me wahi field hai  txtLedgerName8

Ye number tab ka hai aur har baar badal jata hai. Isliye ID kabhi hardcode
nahi ki ja sakti. Ye class chalte waqt suffix dhoondhti hai aur baaki saare
field usi se banati hai. Ek jagah suffix mila -> poora form haath me.
"""
from __future__ import annotations

import re

import re

from playwright.sync_api import Locator

from config.settings import settings
from framework import safety
from framework.base_page import BasePage


class FormNotOpen(RuntimeError):
    pass


class SaveBlocked(RuntimeError):
    """ALLOW_DESTRUCTIVE=false hai -- save jaan-boojh kar roka gaya."""


class TransactionForm:
    # in me se jo bhi mile, uska suffix hi form ka suffix hai
    ANCHORS = ("txtLedgerName", "btnSave", "txtentryNo", "txtbillDate")

    def __init__(self, bp: BasePage):
        self.bp = bp
        self.page = bp.page
        self._suffix: str | None = None

    # ---------- suffix ----------

    def _find_suffix(self) -> str:
        js = r"""
        (anchors) => {
          for (const a of anchors) {
            const el = [...document.querySelectorAll(`[id^="${a}"]`)]
              .find(e => e.offsetHeight > 0 && /\d+$/.test(e.id));
            if (el) return el.id.slice(a.length);
          }
          return null;
        }
        """
        got = self.page.evaluate(js, list(self.ANCHORS))
        if not got:
            raise FormNotOpen(
                "Transaction form khula hi nahi (koi txtLedgerName/btnSave nahi mila).\n"
                f"URL: {self.page.url}"
            )
        return got

    @property
    def suffix(self) -> str:
        if self._suffix is None:
            self._suffix = self._find_suffix()
        return self._suffix

    def refresh(self):
        """Naya tab khula ho to suffix dobara dhoondho."""
        self._suffix = None
        return self.suffix

    def f(self, base: str) -> Locator:
        """Field ka locator -- suffix apne aap lag jayega."""
        return self.page.locator(f"#{base}{self.suffix}")

    # ---------- popup ----------

    def clear_popups(self) -> int:
        """
        Form khulte hi jo popup aate hain unhe hatao:
          - "Set Transaction Preferences"  (Sale Bill pehli baar)
          - "Bill Details"                 (Sale Return)
        Save wale popup pe kabhi OK nahi dabate.
        """
        n = 0
        for _ in range(3):
            m = safety.read_modal(self.page)
            if not m:
                break
            text = (m.get("text") or "").lower()
            # MargBooks ke popup ke PAKKE id (asli project se mile):
            #   #btnYes    -> haan
            #   #btn-Close -> band karo
            #   #btn-Save  -> final save
            for pid, why in (("#btn-Close", "popup band"),):
                try:
                    b = self.page.locator(pid).first
                    if b.is_visible(timeout=600):
                        safety.guarded_click(b, f"modal{pid}", timeout=2500)
                        self.page.wait_for_timeout(700)
                        n += 1
                        break
                except Exception:  # noqa: BLE001
                    continue
            else:
                pass

            if "bill details" in text or "returns of bills" in text:
                try:                       # ye sirf poochta hai, likhta nahi
                    safety.guarded_click(self.page.locator("#ok").first,
                                         "modal.ok", timeout=2500)
                    self.page.wait_for_timeout(900)
                    n += 1
                    continue
                except Exception:  # noqa: BLE001
                    pass
            if safety.dismiss_modal(self.page) or safety.force_close_modal(self.page):
                n += 1
                self.page.wait_for_timeout(700)
            else:
                break
        return n

    # ---------- header fields ----------

    def set_party(self, name: str):
        """
        Party chuno -- ASLI tareeke se.

        Pehle main naam TYPE karta tha. Galat tha. MargBooks me lookup field
        aise chalte hain: click -> SPACE -> #SearchBox popup -> naam -> option
        pe click. Field ke placeholder me likha bhi rehta hai "Press SpaceBar".
        """
        from pages import lookup, form_profile
        el = form_profile.field_locator(self.bp, "party")
        self._picked_party = lookup.pick(self.bp, el, name, what="party")
        self.clear_popups()
        return self

    # ---- form ki tasveer ----

    def profile(self, row: int = 0):
        """
        Is form me kaunse field hain -- ye har trade me alag hota hai.
        Pharma me patient/doctor, general me customer, wholesale me sirf ledger.
        """
        from pages import form_profile
        return form_profile.read(self.bp, row)

    def fill_header(self, party: str, **values):
        """
        Header ke saare field bharo -- par SIRF wo jo is form me maujood hain.

        Yahi is tool ka asli faayda hai: ek hi test pharma, general aur
        wholesale teeno pe chalta hai, kyunki hum pehle dekhte hain ki
        kya-kya hai, phir wahi bharte hain.

        values me jo de sakte ho: customer_name, patient_name, patient_mobile,
        doctor_name, doctor_mobile, mr
        """
        from pages import lookup, form_profile
        prof = self.profile()
        done, skipped = [], []

        self.set_party(party)
        done.append("party")

        # lookup wale field (popup se chunte hain)
        for key in ("customer_name", "patient_name", "mr"):
            if not prof.has(key):
                skipped.append(key)
                continue
            val = values.get(key)
            el = form_profile.field_locator(self.bp, key)
            if val:
                try:
                    lookup.pick(self.bp, el, val, what=key)
                    done.append(key)
                except lookup.LookupFailed:
                    lookup.skip(self.bp, el)
                    skipped.append(f"{key}(nahi mila)")
            else:
                lookup.skip(self.bp, el)      # optional -- chhod do
                skipped.append(f"{key}(khali)")

        # seedhe type wale field
        for key in ("patient_mobile", "doctor_mobile", "doctor_name"):
            if not prof.has(key):
                skipped.append(key)
                continue
            val = values.get(key)
            el = form_profile.field_locator(self.bp, key)
            if val:
                safety.guarded_click(el, f"form.{key}")
                safety.safe_clear(el, self.page)
                el.type(str(val), delay=40)
                el.press("Enter")
                done.append(key)
            else:
                lookup.skip(self.bp, el)
                skipped.append(f"{key}(khali)")

        self.clear_popups()
        return {"trade": prof.trade, "filled": done, "skipped": skipped}

    def get_party(self) -> str:
        return self.f("txtLedgerName").input_value()

    def get_bill_no(self, wait_ms: int = 6000) -> str:
        """
        Bill number. Ye field server se aata hai, isliye form khulne ke turant
        baad khali mil sakta hai -- ek baar khali '' padh ke test jhootha fail
        ho gaya tha. Ab bharne tak intezaar karte hain.
        """
        el = self.f("txtentryNo")
        step, waited = 300, 0
        while waited < wait_ms:
            v = (el.input_value() or "").strip()
            if v:
                return v
            self.page.wait_for_timeout(step)
            waited += step
        return ""

    def get_date(self) -> str:
        return self.f("txtbillDate").input_value()

    def set_bill_discount(self, pct: float):
        el = self.f("txtbillDiscountPercentage")
        safety.guarded_click(el, "form.bill_discount")
        safety.safe_clear(el, self.page)
        el.type(str(pct), delay=40)
        el.press("Tab")
        self.page.wait_for_timeout(800)
        return self

    def set_patient(self, mobile: str = "", name: str = ""):
        if mobile:
            self.f("txtptmobile").fill(mobile)
        if name:
            self.f("txtptname").fill(name)
        return self

    # ---------- totals ----------

    def get_totals(self) -> dict:
        """Screen pe dikh rahe totals padho -- kuch badalte nahi, sirf padhte hain."""
        return self.page.evaluate(r"""
          () => {
            const num = s => {
              const m = (s || '').replace(/,/g, '').match(/-?\d+(\.\d+)?/);
              return m ? parseFloat(m[0]) : null;
            };
            const after = (label) => {
              const nodes = [...document.querySelectorAll('td, label, span, div, a')];
              const hit = nodes.find(e => (e.innerText||'').trim()
                                           .toLowerCase().startsWith(label.toLowerCase()));
              if (!hit) return null;
              const own = num(hit.innerText);
              if (own !== null && !/^[a-z% .]+$/i.test(hit.innerText.trim())) return own;
              let sib = hit.nextElementSibling;
              for (let i = 0; sib && i < 3; i++, sib = sib.nextElementSibling) {
                const v = num(sib.innerText);
                if (v !== null) return v;
              }
              return null;
            };
            return {
              goods_value:   after('Goods Value'),
              cgst:          after('CGST'),
              sgst:          after('SGST'),
              igst:          after('IGST'),
              total_disc:    after('Total Disc'),
              invoice_value: after('Invoice Value'),
              balance:       after('Balance'),
            };
          }
        """)

    # ---------- save / close ----------

    def save(self):
        """
        Bill save karo.

        Ye data LIKHTA hai, isliye ALLOW_DESTRUCTIVE=false hone par jaan-boojh
        kar rok diya jata hai. Guard ko chupchaap bypass karna hi asli khatra hai.
        """
        if not settings.ALLOW_DESTRUCTIVE:
            raise SaveBlocked(
                "save() roka gaya: ALLOW_DESTRUCTIVE=false.\n"
                "  Demo/khaali company pe hi .env me true karna."
            )
        # Save the way a user does: F10 (the first F10 may only leave the grid / stop on Bill Discount),
        # SAVE in the Mode Of Payment window when it opens, the final confirm, then close the Print popup.
        # Afterwards CHECK that it saved: a save that silently did nothing used to pass (live-app check found it).
        page = self.page
        before = self._bill_no_quick()
        printed = False

        def vis(sel: str) -> bool:
            try:
                loc = page.locator(sel)
                return loc.count() > 0 and loc.first.is_visible()
            except Exception:  # noqa: BLE001
                return False

        for _ in range(6):
            if vis("#BalanceAdjusted"):                                   # Mode Of Payment window
                self._mop_seen = True
                for sel in ("#btn-Save", ".modal.show button:has-text('SAVE')", "ngb-modal-window button:has-text('SAVE')"):
                    if vis(sel):
                        safety.guarded_click(page.locator(sel).first, "mop.save", timeout=5000, inside_modal=True)
                        break
                self.bp.settle(quiet_ms=800, timeout_ms=25000)
                continue
            if vis("#btn-Close") or page.get_by_text("Select Format", exact=False).count():   # Print popup: saved
                printed = True
                if vis("#btn-Close"):
                    safety.guarded_click(page.locator("#btn-Close").first, "preview.close", timeout=4000, inside_modal=True)
                else:
                    page.keyboard.press("Escape")
                page.wait_for_timeout(800)
                break
            if vis("#btnYes") and self._save_confirm():                   # e.g. "Allow Without Bill No.?"
                safety.guarded_click(page.locator("#btnYes").first, "form.save_confirm", timeout=5000, inside_modal=True)
                self.bp.settle(quiet_ms=800, timeout_ms=25000)
                continue
            if vis("#btn-Save"):                                          # final confirm
                safety.guarded_click(page.locator("#btn-Save").first, "form.final_save", timeout=5000, inside_modal=True)
                self.bp.settle(quiet_ms=800, timeout_ms=25000)
                continue
            if self._saved_since(before):
                break
            safety.audit_key("F10", "form.save")
            page.keyboard.press("F10")
            self.bp.settle(quiet_ms=800, timeout_ms=25000)
            page.wait_for_timeout(600)

        if not (printed or self._saved_since(before)):
            raise SaveBlocked(f"The bill was not saved: the form still shows bill {before or '(no number)'} with its "
                              f"lines after F10 / Save. A message or a required field may be stopping the save.")
        self.clear_popups()
        return self

    # Questions the app asks while SAVING that a user answers Yes to in order to finish the save. Only these are
    # answered: a different Yes/No (delete, leave without saving) is never clicked by save().
    SAVE_CONFIRMS = ("allow without bill no",)

    def _save_confirm(self) -> bool:
        try:
            txt = self.page.evaluate("""() => [...document.querySelectorAll('ngb-modal-window, .modal.show, .swal2-popup')]
                .filter(m => m.getClientRects().length).map(m => m.innerText).join(' ')""")
        except Exception:  # noqa: BLE001
            return False
        low = " ".join(str(txt).lower().split())
        return any(c in low for c in self.SAVE_CONFIRMS)

    def _bill_no_quick(self) -> str:
        try:
            el = self.page.locator("[id^='txtentryNo']").first
            return (el.input_value(timeout=1500) or "").strip() if el.count() else ""
        except Exception:  # noqa: BLE001
            return ""

    def _saved_since(self, before: str) -> bool:
        """Saved = a 'saved' message is on screen, or the form moved on (new bill number, or the form closed)."""
        try:
            if self.page.get_by_text(re.compile(r"(saved|updated) successfully", re.I)).count():
                return True
        except Exception:  # noqa: BLE001
            pass
        now = self._bill_no_quick()
        if before and now and now != before:
            return True
        try:
            if not self.page.locator("[id^='txtentryNo']").count():
                return True                     # the bill form is gone (e.g. back on the list after an update)
        except Exception:  # noqa: BLE001
            pass
        return False

    def close(self):
        """Form band karo -- BINA save kiye. Ye hamesha surakshit hai."""
        try:
            safety.guarded_click(self.f("btnEsc").first, "form.close", timeout=3000)
        except Exception:  # noqa: BLE001
            safety.audit_key("Escape", "form.close")
            self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(1000)
        # "Transaction data will be loss, Are you sure?" -> Yes
        safety.dismiss_modal(self.page)
        self.page.wait_for_timeout(800)
        self._suffix = None
        return self

    # ---------- diagnosis ----------

    def snapshot(self) -> dict:
        """Form ki abhi ki haalat -- test ke failure message me kaam aata hai."""
        try:
            return {
                "suffix": self.suffix,
                "party": self.get_party(),
                "bill_no": self.get_bill_no(),
                "date": self.get_date(),
                "totals": self.get_totals(),
                "url": self.page.url,
            }
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)[:150], "url": self.page.url}
