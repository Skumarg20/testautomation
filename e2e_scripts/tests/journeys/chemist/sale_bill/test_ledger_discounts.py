"""Party discounts set in the Ledger Master (master discount and special rate) must appear on a new bill."""

from dataclasses import replace

import pytest

from pages.sale.chemist.ledger_master_discount_page import LedgerMasterDiscountPage
from pages.sale.chemist.ledger_special_discount_page import LedgerSpecialDiscountPage
from pages.sale.chemist.sale_bill import SaleBill
from test_data.discounts import LEDGER_MASTER_DISCOUNT, LEDGER_SPECIAL_DISCOUNT, DiscountCase
from test_data.models import HeaderTag, ItemEntry

pytestmark = [
    pytest.mark.p1,
    pytest.mark.journey("ledger-discounts"),
    pytest.mark.xdist_group("chemist-tenant"),
]

ONE_UNIT = 1


def _only(case: DiscountCase, **kept: bool) -> DiscountCase:
    """The case with every discount cleared except the ones named, e.g. `_only(case, discount1=True)`."""
    cleared = {name: None for name in ("discount1", "discount2", "volume_discount1", "volume_discount2")}
    keep = {name: getattr(case, name) for name, wanted in kept.items() if wanted}
    return replace(case, **{**cleared, **keep})


def _add_one_unit(sale_bill: SaleBill, case: DiscountCase) -> None:
    sale_bill.add_item(0, ItemEntry(description=case.item_description, quantity=ONE_UNIT))


class TestLedgerMasterDiscount:
    PARTY = LEDGER_MASTER_DISCOUNT.party_name or ""

    @pytest.mark.parametrize("field", ["discount1", "discount2"])
    def test_single_master_discount_appears_on_a_new_bill(
        self,
        ledger_master: LedgerMasterDiscountPage,
        sale_bill: SaleBill,
        field: str,
    ) -> None:
        case = _only(LEDGER_MASTER_DISCOUNT, **{field: True})
        ledger_master.set_discounts(self.PARTY, case)
        sale_bill.start(HeaderTag.MASTER_DISCOUNT)

        _add_one_unit(sale_bill, case)

        shown = sale_bill.discount1_of(0) if field == "discount1" else sale_bill.discount2_of(0)
        assert shown == getattr(case, field)

    def test_both_master_discounts_appear_on_a_new_bill(
        self, ledger_master: LedgerMasterDiscountPage, sale_bill: SaleBill
    ) -> None:
        ledger_master.set_discounts(self.PARTY, LEDGER_MASTER_DISCOUNT)
        sale_bill.start(HeaderTag.MASTER_DISCOUNT)

        _add_one_unit(sale_bill, LEDGER_MASTER_DISCOUNT)

        assert sale_bill.discount1_of(0) == LEDGER_MASTER_DISCOUNT.discount1
        assert sale_bill.discount2_of(0) == LEDGER_MASTER_DISCOUNT.discount2


class TestLedgerSpecialDiscount:
    PARTY = LEDGER_SPECIAL_DISCOUNT.party_name or ""

    @pytest.mark.parametrize("field", ["discount1", "discount2", "volume_discount1"])
    def test_single_special_discount_appears_on_a_new_bill(
        self,
        ledger_special: LedgerSpecialDiscountPage,
        sale_bill: SaleBill,
        field: str,
    ) -> None:
        case = _only(LEDGER_SPECIAL_DISCOUNT, **{field: True})
        ledger_special.set_special_rates(self.PARTY, case)
        sale_bill.start(HeaderTag.SPECIAL_DISCOUNT)

        _add_one_unit(sale_bill, case)

        readers = {
            "discount1": sale_bill.discount1_of,
            "discount2": sale_bill.discount2_of,
            "volume_discount1": sale_bill.volume_discount1_of,
        }
        assert readers[field](0) == getattr(case, field)

    def test_all_special_discounts_appear_on_a_new_bill(
        self, ledger_special: LedgerSpecialDiscountPage, sale_bill: SaleBill
    ) -> None:
        ledger_special.set_special_rates(self.PARTY, LEDGER_SPECIAL_DISCOUNT)
        sale_bill.start(HeaderTag.SPECIAL_DISCOUNT)

        _add_one_unit(sale_bill, LEDGER_SPECIAL_DISCOUNT)

        assert sale_bill.discount1_of(0) == LEDGER_SPECIAL_DISCOUNT.discount1
        assert sale_bill.discount2_of(0) == LEDGER_SPECIAL_DISCOUNT.discount2
        assert sale_bill.volume_discount1_of(0) == LEDGER_SPECIAL_DISCOUNT.volume_discount1
