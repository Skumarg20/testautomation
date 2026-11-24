"""Contract C4: test data. Every record carries run_id so it can be cleaned up."""

from dataclasses import replace
from decimal import Decimal

from test_data.gst_calc import GST_SLABS
from test_data.models import (
    HOME_STATE_CODE,
    ItemMasterSpec,
    ItemSpec,
    PartySpec,
    PurchaseBillSpec,
    PurchaseLine,
)

_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_CHECKSUM_BASE = len(_CHARS)
_GSTIN_BODY_LENGTH = 14
_DEFAULT_STATE_CODE = "27"
OTHER_STATE_CODE = "27"
UNIT_PRICE = Decimal("100.00")
SLAB_RATES = tuple(sorted(rate for rate in GST_SLABS if rate != 40))
# Masters seen on the QA tenant 2026-10-08 (specs/item-master-crud.md); tests pick them, never create them.
ITEM_UNIT = "PCS"
ITEM_HSN = "12345678"
ITEM_TAX_CATEGORY = "GST Sale - 12%"
ITEM_GST_RATE = Decimal("12")
ITEM_COMPANY = "Others"
ITEM_MRP = Decimal("200.00")
ITEM_SALE_RATE = Decimal("150.00")
EDITED_HSN = "54545454"
EDITED_SALE_RATE = Decimal("175.00")


def _gstin_check_char(body: str) -> str:
    total = 0
    for position, char in enumerate(body[:_GSTIN_BODY_LENGTH]):
        weighted = _CHARS.index(char) * (1 if position % 2 == 0 else 2)
        total += weighted // _CHECKSUM_BASE + weighted % _CHECKSUM_BASE
    return _CHARS[(_CHECKSUM_BASE - total % _CHECKSUM_BASE) % _CHECKSUM_BASE]


class DataFactory:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._party_count = 0

    def valid_gstin(self, state_code: str = _DEFAULT_STATE_CODE) -> str:
        body = f"{state_code}ABCDE1234F1Z"
        return body + _gstin_check_char(body)

    def invalid_gstin(self, state_code: str = _DEFAULT_STATE_CODE) -> str:
        """A well-formed GSTIN whose check character is wrong."""
        valid = self.valid_gstin(state_code)
        wrong_check_char = "1" if valid.endswith("0") else "0"
        return valid[:-1] + wrong_check_char

    def party_name(self, label: str = "Party") -> str:
        self._party_count += 1
        return f"QA-{self.run_id}-{label}-{self._party_count}"

    def intra_state_party(self) -> PartySpec:
        return self._registered_party("Intra", HOME_STATE_CODE)

    def inter_state_party(self) -> PartySpec:
        return self._registered_party("Inter", OTHER_STATE_CODE)

    def unregistered_party(self) -> PartySpec:
        return PartySpec(self.party_name("Unreg"), HOME_STATE_CODE)

    def party_with_invalid_gstin(self) -> PartySpec:
        gstin = self.invalid_gstin(HOME_STATE_CODE)
        return PartySpec(self.party_name("BadGstin"), HOME_STATE_CODE, gstin)

    def item_for_slab(self, gst_rate: Decimal) -> ItemSpec:
        return ItemSpec(f"QA-{self.run_id}-Slab{gst_rate}", gst_rate, UNIT_PRICE)

    def items_per_slab(self) -> tuple[ItemSpec, ...]:
        return tuple(self.item_for_slab(rate) for rate in SLAB_RATES)

    def item_master(self) -> ItemMasterSpec:
        """A new item with only the mandatory fields plus M.R.P and sale rate."""
        return ItemMasterSpec(
            product=f"QA-{self.run_id}-Item",
            unit=ITEM_UNIT,
            hsn=ITEM_HSN,
            tax_category=ITEM_TAX_CATEGORY,
            gst_rate=ITEM_GST_RATE,
            company=ITEM_COMPANY,
            mrp=ITEM_MRP,
            sale_rate=ITEM_SALE_RATE,
        )

    @staticmethod
    def edited_item(item: ItemMasterSpec) -> ItemMasterSpec:
        """The same item with another existing HSN and a new sale rate, as typed in Modify Item."""
        return replace(item, hsn=EDITED_HSN, sale_rate=EDITED_SALE_RATE)

    def purchase_bill(self, supplier: PartySpec, items: tuple[ItemSpec, ...]) -> PurchaseBillSpec:
        lines = tuple(PurchaseLine(item, quantity=1, rate=item.price) for item in items)
        return PurchaseBillSpec(supplier, f"INV-{self.run_id}", lines)

    def _registered_party(self, label: str, state_code: str) -> PartySpec:
        return PartySpec(self.party_name(label), state_code, self.valid_gstin(state_code))
