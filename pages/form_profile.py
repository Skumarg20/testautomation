"""
Form ko PADHO, phir bharo. Yahi is tool ka asli dimaag hai.

KYUN ZAROORI HAI
----------------
Sale Bill har trade me alag dikhta hai:

    Pharma / Chemist  ->  Patient Mob., Patient Name, Doctor Mob., Doctor Name,
                          MR, Batch, Expiry
    General trade     ->  Customer Name (patient/doctor kuch nahi)
    Wholesale         ->  sirf Ledger, na patient na customer
    Supermarket       ->  barcode-first, batch aksar nahi

Aur upar se Control Room ki settings kuch field on/off kar deti hain
(Mode of Payment, Bill Discount, Item Discount...).

Main ab tak ek FIXED script likh raha tha: party -> patient -> doctor -> item.
Wo pharma pe bhi tabhi chalta jab saari settings on hon, aur general trade pe
kabhi nahi. Isliye saare sale test red the.

SAHI TAREEKA
------------
Form khulne par uske field GINO, phir sirf wahi bharo jo waha hain.
Jo nahi hai use chhod do -- wo galti nahi hai, us trade me wo field hota hi nahi.

Isse ek hi test pharma, general aur wholesale teeno pe chal jata hai.
"""
from __future__ import annotations

from framework.base_page import BasePage
from pages import ag_grid

# Header ke field. Har ek ka formcontrolname ya id ka pattern.
# "kya ye zaroori hai" ka jawab trade se aata hai, isliye yahan sirf pehchan.
HEADER_FIELDS: dict[str, dict] = {
    "party":          {"sel": '[formcontrolname="ledgerName"], input[id^="txtLedgerName"]',
                       "label": "Party / Ledger"},
    "bill_no":        {"sel": 'input[id^="txtentryNo"]', "label": "Bill No."},
    "date":           {"sel": 'input[id^="txtbillDate"]', "label": "Date"},
    "customer_name":  {"sel": '[formcontrolname="customerName"], [formcontrolname="CustomerName"]',
                       "label": "Customer Name"},
    "patient_mobile": {"sel": '[formcontrolname="PatientMobile"], input[id^="txtptmobile"]',
                       "label": "Patient Mob."},
    "patient_name":   {"sel": '[formcontrolname="PatientName"], input[id^="txtptname"]',
                       "label": "Patient Name"},
    "doctor_mobile":  {"sel": '[formcontrolname="doctorMobileNo"], input[id^="txtdrmobile"]',
                       "label": "Doctor Mob."},
    "doctor_name":    {"sel": '[formcontrolname="DoctorName"], input[id^="txtdrname"]',
                       "label": "Doctor Name"},
    "mr":             {"sel": '[formcontrolname="mrName"]', "label": "MR"},
    "bill_type":      {"sel": '[formcontrolname="billTypeName"]', "label": "Sale Type"},
    "address":        {"sel": 'input[id^="txtpatientaddress"]', "label": "Address"},
    "bill_discount":  {"sel": 'input[id^="txtbillDiscountPercentage"]',
                       "label": "Bill Discount"},
}

PROBE_JS = r"""
(spec) => {
  const out = {};
  for (const [key, sel] of Object.entries(spec)) {
    const el = document.querySelector(sel);
    if (!el) { out[key] = null; continue; }
    const r = el.getBoundingClientRect();
    out[key] = {
      present: true,
      visible: r.width > 0 && r.height > 0,
      disabled: !!el.disabled || el.getAttribute('readonly') !== null,
      value: (el.value || '').trim(),
      id: el.id || '',
      tag: el.tagName.toLowerCase(),
    };
  }
  return out;
}
"""


class FormProfile:
    """Ek khule hue transaction form ki tasveer."""

    def __init__(self, fields: dict, grid_cols: list[dict], grid_fields: list[str]):
        self.fields = fields
        self.grid_cols = grid_cols
        self.grid_fields = grid_fields

    # ---- kya hai, kya nahi ----

    def has(self, name: str) -> bool:
        f = self.fields.get(name)
        return bool(f and f.get("visible") and not f.get("disabled"))

    def present(self) -> list[str]:
        return [k for k in self.fields if self.has(k)]

    def missing(self) -> list[str]:
        return [k for k in self.fields if not self.has(k)]

    def has_grid_field(self, name: str) -> bool:
        return name in self.grid_fields

    # ---- trade ka andaza ----

    @property
    def trade(self) -> str:
        """
        Form dekh kar trade ka andaza. Ye label lagane ke liye hai --
        faisla hamesha "field hai ya nahi" se hota hai, trade ke naam se nahi.
        Warna hum wahi purani galti dohrayenge: pehle maan lena, phir bharna.
        """
        if self.has("patient_name") or self.has("doctor_name") or self.has("mr"):
            return "pharma"
        if self.has("customer_name"):
            return "general"
        if self.has("party") and not self.has("customer_name"):
            return "wholesale"
        return "unknown"

    @property
    def needs_batch(self) -> bool:
        return self.has_grid_field("batch") or any(
            c["id"] in ("batchName", "expiryDate") for c in self.grid_cols)

    def summary(self) -> str:
        return (f"trade={self.trade} | header: {', '.join(self.present()) or '(kuch nahi)'}"
                f" | grid: {', '.join(self.grid_fields) or '(kuch nahi)'}")

    def as_dict(self) -> dict:
        return {
            "trade": self.trade,
            "present": self.present(),
            "missing": self.missing(),
            "grid_fields": self.grid_fields,
            "grid_columns": [c["id"] for c in self.grid_cols],
            "needs_batch": self.needs_batch,
        }


def read(bp: BasePage, row: int = 0) -> FormProfile:
    """Khule hue form ko padho."""
    spec = {k: v["sel"] for k, v in HEADER_FIELDS.items()}
    try:
        fields = bp.page.evaluate(PROBE_JS, spec) or {}
    except Exception:  # noqa: BLE001
        fields = {}
    return FormProfile(
        fields=fields,
        grid_cols=ag_grid.columns(bp.page),
        grid_fields=ag_grid.available_fields(bp.page, row),
    )


def field_locator(bp: BasePage, name: str):
    """Profile ke naam se asli locator."""
    spec = HEADER_FIELDS.get(name)
    if not spec:
        raise KeyError(f"'{name}' form ka koi field nahi. Ye hain: {sorted(HEADER_FIELDS)}")
    return bp.page.locator(spec["sel"]).first
