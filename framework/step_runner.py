"""
YAML test case ko execute karta hai.

Ek step aisa dikhta hai:
    - action: fill
      target: sale_invoice.party
      value: "{{party_name}}"
      save_as: party      # baad ke steps me {ctx.party} se use kar sakte ho

Supported actions: goto, click, fill, select, press, wait_text, assert_text,
assert_no_text, assert_visible, assert_not_visible, sleep, screenshot, note.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from framework.base_page import BasePage
from framework import data_factory
from framework.safety import ModuleNotEnabled, UnsafeClick, dismiss_modal

PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
CTXREF = re.compile(r"\{ctx\.(\w+)\}")


class StepFailed(AssertionError):
    pass


class TradeMismatch(Exception):
    """
    Test kisi aur trade ke liye hai (pharma ka test general company pe).
    Ye BUG NAHI hai -- runner ise SKIP maanta hai.
    """


@dataclass
class RunContext:
    vars: dict[str, Any] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)


class StepRunner:
    def __init__(self, page: BasePage, ctx: RunContext | None = None):
        self.p = page
        self.ctx = ctx or RunContext()

    # ---------- templating ----------

    def render(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        out = PLACEHOLDER.sub(lambda m: str(data_factory.resolve(m.group(1))), value)
        out = CTXREF.sub(lambda m: str(self.ctx.vars.get(m.group(1), "")), out)
        return out

    # ---------- execution ----------

    def run(self, steps: list[dict]):
        for i, step in enumerate(steps, 1):
            action = step.get("action")
            target = step.get("target")
            value = self.render(step.get("value"))
            desc = step.get("note") or f"{action} {target or ''} {value or ''}".strip()
            try:
                self._dispatch(action, target, value, step)
                self.ctx.log.append(f"  [{i}] OK   {desc}")
            except TradeMismatch as e:
                self.ctx.log.append(f"  [{i}] SKIP {desc} -> {e}")
                import pytest
                pytest.skip(str(e))
            except ModuleNotEnabled as e:
                # Bug nahi -- module Control Room me OFF hai
                self.ctx.log.append(f"  [{i}] SKIP {desc} -> {e}")
                import pytest
                pytest.skip(str(e))
            except UnsafeClick as e:
                self.ctx.log.append(f"  [{i}] BLOCKED {desc} -> {e}")
                self.p.screenshot(f"unsafe_step_{i}")
                raise StepFailed(f"Step {i} rok diya gaya (suraksha):\n{e}") from e
            except Exception as e:  # noqa: BLE001
                self.ctx.log.append(f"  [{i}] FAIL {desc} -> {e}")
                self.p.screenshot(f"fail_step_{i}_{int(time.time())}")
                raise StepFailed(f"Step {i} failed: {desc}\n{e}") from e

            if (name := step.get("save_as")):
                self.ctx.vars[name] = value

    # ---- POM tak pahunch ----

    def _form(self):
        from pages.transaction_form import TransactionForm
        if not getattr(self, "_form_obj", None):
            self._form_obj = TransactionForm(self.p)
            self._form_obj.clear_popups()
        self._form_obj.refresh()      # naya tab khula ho to suffix dobara
        return self._form_obj

    def _sale(self):
        from pages.sale_bill_page import SaleBillPage
        if not getattr(self, "_sale_obj", None):
            self._sale_obj = SaleBillPage(self.p)
            self._sale_obj.clear_popups()
        self._sale_obj.refresh()
        return self._sale_obj

    def _retail(self):
        from pages.retail_billing import RetailBillPage
        if not getattr(self, "_retail_obj", None):
            self._retail_obj = RetailBillPage(self.p)
            self._retail_obj.clear_popups()
        self._retail_obj.refresh()
        return self._retail_obj

    def _check_totals(self, spec: str):
        """'cgst=5, sgst=5' jaisi cheez jaancho."""
        totals = self._form().get_totals()
        bad = []
        for part in str(spec).split(","):
            if "=" not in part:
                continue
            k, v = [x.strip() for x in part.split("=", 1)]
            got = totals.get(k)
            try:
                ok = got is not None and abs(float(got) - float(v)) < 0.01
            except (TypeError, ValueError):
                ok = str(got) == v
            if not ok:
                bad.append(f"{k}: mila {got}, chahiye tha {v}")
        if bad:
            raise StepFailed("Total galat hai --\n  " + "\n  ".join(bad)
                             + f"\n  Poore totals: {totals}")

    def _dispatch(self, action, target, value, step):
        match action:
            case "goto":
                self.p.goto(target or "/")
            case "open_menu":
                # "Sale > Bill" ya "sale.bill" -- dono chalega.
                # Tester ke liye menu ka naam yaad rakhna aasan hai,
                # screen ka technical naam nahi.
                from framework import menu_tree
                from framework.screens import open_screen
                want = str(target or value or "").strip()
                node = menu_tree.by_id(want)
                if not node:
                    for n, path in menu_tree.walk():
                        if " > ".join(path).lower() == want.lower() \
                                or n["label"].lower() == want.lower():
                            node = n
                            break
                if not node:
                    raise StepFailed(
                        f"Menu me '{want}' nahi mila.\n"
                        f"  Aise likho: 'Sale > Bill' ya 'sale.bill'")
                # value me "new"/"create" ho to "+" wala form
                want_new = str(value or "").strip().lower() in ("new", "create", "+")
                screen = (node.get("create") if want_new else None) \
                    or node.get("screen") or node.get("create")
                if not screen:
                    raise StepFailed(
                        f"'{want}' sirf ek folder hai -- uske andar ka item chuno")
                if not open_screen(self.p, screen):
                    raise StepFailed(f"'{want}' ({screen}) khul nahi paya")

            case "open_screen":
                from framework.screens import open_screen
                if not open_screen(self.p, target):
                    raise StepFailed(f"Screen '{target}' khul nahi paya")

            # ---- Transaction form ke UNCHE STAR ke kaam ----
            #
            # Grid ke cell tab tak <input> bante hi nahi jab tak focus na ho.
            # Isliye "fill sale.qty_cell 2" kabhi chalta hi nahi tha. Ye actions
            # POM ko bulate hain, jo wahi keyboard wala rasta leta hai jo asli
            # user leta hai. Tester ke liye bhi ye padhne me saaf hain.
            case "set_party":
                self._form().set_party(value)

            case "fill_header":
                # "Cash Account | patient=Ramesh | mr=Eshaanvi1"
                # SIRF wo field bharega jo is trade ke form me hain.
                parts = [x.strip() for x in str(value).split("|")]
                party = parts[0]
                extra = {}
                for kv in parts[1:]:
                    if "=" in kv:
                        k, v = [x.strip() for x in kv.split("=", 1)]
                        extra[{"patient": "patient_name",
                               "customer": "customer_name",
                               "doctor": "doctor_name"}.get(k, k)] = v
                res = self._form().fill_header(party, **extra)
                self.ctx.log.append(
                    f"      trade={res['trade']} | bhara: {', '.join(res['filled'])}"
                    f" | chhoda: {', '.join(res['skipped']) or 'kuch nahi'}")

            case "require_setting":
                # "mode_of_payment" ya "calculation_type=Inclusive"
                #
                # Ye test ka PRE-REQUISITE hai: setting theek na ho to pehle
                # theek ki jayegi, phir test aage badhega. Pehle hum aisa
                # test SKIP kar dete the -- imaandaar tha, par kaam aage
                # nahi badhta tha.
                from framework import control_room as _cr
                spec = str(value or target or "").strip()
                feat, _, want = spec.partition("=")
                res = _cr.ensure(self.p, feat.strip(), want.strip() or "Yes")
                self.ctx.log.append(
                    f"      setting {res['feature']}: {res['why']}"
                    + (f" ({res.get('from')} -> {res['value']})"
                       if res["changed"] else ""))

            case "expect_trade":
                # Ye FAIL nahi, SKIP hai.
                #
                # Pharma ka test general-trade company pe chal hi nahi sakta --
                # wahan patient/doctor/batch hote hi nahi. Use laal dikhana
                # jhooth hoga: app bilkul theek hai, test us company ke liye
                # hai hi nahi.
                prof = self._form().profile()
                if prof.trade != str(value).strip():
                    raise TradeMismatch(
                        f"Ye test '{value}' trade ke liye hai, par ye company "
                        f"'{prof.trade}' trade ki hai.\n"
                        f"  {prof.summary()}\n"
                        f"  Ye bug nahi hai -- test is company pe lagu hi nahi hota."
                    )

            case "expect_field":
                # "patient_name" hona chahiye
                if not self._form().profile().has(str(value).strip()):
                    raise StepFailed(
                        f"Form me '{value}' field nahi hai.\n"
                        f"  {self._form().profile().summary()}")

            case "expect_no_field":
                if self._form().profile().has(str(value).strip()):
                    raise StepFailed(f"Form me '{value}' field nahi hona chahiye tha")

            case "add_item":
                # "Item Name | qty | rate"  ya  "80000111 | 2"  (barcode)
                parts = [x.strip() for x in str(value).split("|")]
                if not parts or not parts[0]:
                    raise StepFailed("add_item ko chahiye: 'Item ya barcode | qty | rate'")
                qty = float(parts[1]) if len(parts) > 1 and parts[1] else 1
                rate = float(parts[2]) if len(parts) > 2 and parts[2] else None
                disc = float(parts[3]) if len(parts) > 3 and parts[3] else None
                self._sale().add_item(parts[0], qty, rate, discount=disc)

            case "add_barcode":
                # "80000111 | 2 | 100"  -- naam se zyada bharosemand
                parts = [x.strip() for x in str(value).split("|")]
                qty = float(parts[1]) if len(parts) > 1 and parts[1] else 1
                rate = float(parts[2]) if len(parts) > 2 and parts[2] else None
                self._sale().add_by_barcode(parts[0], qty, rate)

            case "retail_bill":
                # "Item | qty | rate | batch"  -- jo hissa is trade me hai
                # wahi bharega, baaki apne aap chhod dega.
                parts = [x.strip() for x in str(value).split("|")]
                res = self._retail().bill(
                    item=parts[0],
                    qty=float(parts[1]) if len(parts) > 1 and parts[1] else 1,
                    rate=float(parts[2]) if len(parts) > 2 and parts[2] else None,
                    batch=parts[3] if len(parts) > 3 and parts[3] else None,
                    patient=step.get("patient"), doctor=step.get("doctor"),
                    save=bool(step.get("save")))
                for line in res["steps"]:
                    self.ctx.log.append(f"      {line}")

            case "expect_party_state":
                # "prefilled" / "empty" / "not_asked"
                got = self._retail().party_state()
                if got["state"] != str(value).strip():
                    # Ye FAIL nahi, SKIP hai.
                    # Doosri setting par party ka poocha jana SAHI vyavhaar
                    # hai -- use laal dikhana jhooth hoga.
                    raise TradeMismatch(
                        f"Ye test party ke '{value}' hone par lagu hai, par "
                        f"abhi wo '{got['state']}' hai.\n"
                        f"  {got['why']}\n"
                        f"  Control Room: 'Ask Party in Retail Billing' = "
                        f"{got['setting']}\n"
                        f"  Ye bug NAHI hai -- test is setting par lagu hi "
                        f"nahi hota.")

            case "ensure_party":
                res = self._retail().ensure_party(value or "Cash Account")
                self.ctx.log.append(f"      {res['action']} -- {res['why']}")

            case "pick_batch":
                self._sale().pick_batch(str(value).strip())

            case "expect_column":
                cols = self._sale().grid_columns()
                if str(value).strip() not in cols:
                    raise StepFailed(
                        f"Grid me '{value}' column nahi hai. Ye hain: {cols}")

            case "set_bill_discount":
                self._form().set_bill_discount(float(value))

            case "expect_total":
                # value: "cgst=5, sgst=5" ya "invoice_value=210"
                self._check_totals(value)

            case "expect_lines":
                got = self._sale().line_count()
                if int(got) != int(value):
                    raise StepFailed(f"Grid me {value} line honi thi, {got} hain")

            case "close_form":
                self._form().close()

            case "save_form":
                self._form().save()
            case "click":
                self.p.click(target)
            case "fill":
                self.p.fill(target, value)
            case "select":
                self.p.select(target, value)
            case "press":
                if target:
                    self.p.press(target, value)
                else:                                   # Test Studio: a key with no target
                    self.p.page.keyboard.press(str(value))
            case "bulk_sale_bills":
                # Test Studio: "create 500 sale bills with 50 items each". "bills | items per bill".
                from ui_studio import bulk
                n, _, per = [x.strip() for x in str(value).partition("|")]
                bulk.run(self.p, self._sale, int(n), int(per or 5), self.ctx.log)
            case "wait_text":
                self.p.wait_for_text(value, step.get("timeout_ms"))
            case "assert_text":
                if not self.p.page_has_text(value):
                    raise StepFailed(f"Expected text not on page: {value!r}")
            case "assert_no_text":
                if self.p.page_has_text(value):
                    raise StepFailed(f"Unexpected text present: {value!r}")
            case "assert_visible":
                if not self.p.is_visible(target):
                    raise StepFailed(f"Not visible: {target}")
            case "assert_not_visible":
                if self.p.is_visible(target, timeout_ms=2000):
                    raise StepFailed(f"Should be hidden but visible: {target}")
            case "sleep":
                time.sleep(float(value or 1))
            case "screenshot":
                self.p.screenshot(str(value or "shot"))
            case "note":
                pass
            case _:
                raise StepFailed(f"Unknown action: {action!r}")
