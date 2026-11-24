"""Offline checks of the round-2 C1 arithmetic, scheme payload and option helpers (no app needed)."""

from decimal import Decimal

import pytest

from pages.masters.round2_c1.scheme_payload import (
    Basis,
    Criteria,
    OfferType,
    SchemeItem,
    SchemeSpec,
    SchemeType,
    Session,
    Slab,
    build_payload,
)
from pages.sale.round2_c1.cells import number_text
from pages.sale.round2_c1.deal_math import (
    all_scheme_free,
    base_quantity,
    charge_by_percentage,
    charge_tax,
    full_scheme_free,
    half_scheme_free,
    lot_rate_by_deal,
    lot_rate_by_percentage,
    reverse_free,
    volume_discount,
    whole_scheme_net_free,
)

pytestmark = pytest.mark.framework

SESSION = Session(7, 8, "qa", 0, "2026-04-01", "2027-03-31")
ITEM = SchemeItem(11, 12, 13)


def test_full_scheme_is_whole_deals_only() -> None:
    assert full_scheme_free(25, (10, 1)) == 2
    assert full_scheme_free(9, (10, 1)) == 0


def test_half_and_all_schemes_are_proportional() -> None:
    assert half_scheme_free(4, (10, 1)) == 0
    assert half_scheme_free(10, (10, 1)) == 1
    assert all_scheme_free(25, (10, 1)) == Decimal("2.5")
    assert reverse_free(25, (10, 1)) == Decimal("2.5")


@pytest.mark.parametrize(("quantity", "expected"), [(9, "0.81"), (10, "1.00"), (15, "1.45")])
def test_whole_scheme_with_net_scheme_formula_one(quantity: int, expected: str) -> None:
    assert whole_scheme_net_free(quantity, (10, 1), 1) == Decimal(expected)


def test_lot_rate_examples_of_the_knowledge_base() -> None:
    assert lot_rate_by_percentage(Decimal(100), Decimal(10)) == Decimal("90.91")
    assert lot_rate_by_deal(Decimal(100), (10, 1)) == Decimal("90.91")


def test_additional_charge_arithmetic() -> None:
    assert charge_by_percentage(Decimal(1000), Decimal(0), Decimal(5)) == Decimal("50.00")
    assert charge_by_percentage(Decimal(1000), Decimal(100), Decimal(10)) == Decimal("90.00")
    assert charge_tax(Decimal(100), Decimal(18)) == Decimal("18.00")


def test_multi_unit_and_volume_modes() -> None:
    assert base_quantity(1, 5, 10) == 15
    line = (10, Decimal(1000))
    assert volume_discount("perUnit", Decimal(5), line) == Decimal("50.00")
    assert volume_discount("Lumpsum", Decimal(5), line) == Decimal("5.00")
    assert volume_discount("Percentage", Decimal(5), line) == Decimal("50.00")
    assert volume_discount("No", Decimal(5), line) == Decimal("0.00")


def test_number_text_accepts_commas_and_trailing_zeros() -> None:
    pattern = number_text(Decimal("1500"))
    assert pattern.match("1,500.00")
    assert not pattern.match("1,501")
    assert number_text(Decimal("0.81")).match("0.81")


def test_scheme_payload_for_a_free_same_item_slab() -> None:
    slab = Slab(Basis.AT_LEAST, 10, OfferType.FREE_SAME_ITEM, 1)
    spec = SchemeSpec("QA-x", SchemeType.ITEM_FREE_DISCOUNT, Criteria.ITEM, (slab,))

    body = build_payload(spec, ITEM, SESSION)

    detail = body["SchemeDetails"][0]
    assert (body["schemetype"], body["selectioncriteria"], body["complinkid"]) == (1, 1, 7)
    assert (detail["itemlinkid"], detail["unitlinkid"], detail["basis"], detail["fromqty"]) == (11, 12, 2, 10)
    assert detail["SchemeFreeItemDetails"][0]["freeitemlinkid"] == 11
    assert len(body["SchemeApplicability"][0]["daylist"]) == 7


def test_scheme_payload_by_company_and_bill_value() -> None:
    company = SchemeSpec(
        "c",
        SchemeType.BUY_X_GET_Y,
        Criteria.COMPANY,
        (Slab(Basis.AT_LEAST, 3, OfferType.DIFF_DISCOUNT_PERCENT, 10),),
    )
    bill = SchemeSpec(
        "b",
        SchemeType.BILL_VALUE,
        Criteria.ITEM,
        (Slab(Basis.AT_LEAST, 0, OfferType.DIFF_DISCOUNT_PERCENT, 10, from_amount=500),),
    )

    by_company = build_payload(company, ITEM, SESSION)["SchemeDetails"][0]
    by_bill = build_payload(bill, ITEM, SESSION)["SchemeDetails"][0]

    assert (by_company["agencylinkid"], by_company["itemlinkid"]) == (13, 0)
    assert (by_bill["fromamt"], by_bill["fromqty"]) == (500, 0)


def test_scheme_payload_for_combo_and_no_scheme() -> None:
    slab = Slab(Basis.AT_LEAST, 2, OfferType.DIFF_DISCOUNT_PERCENT, 10)
    combo = build_payload(SchemeSpec("c", SchemeType.COMBO_OFFER, Criteria.ITEM, (slab,)), ITEM, SESSION)
    none = build_payload(SchemeSpec("n", SchemeType.NO_SCHEME, Criteria.ITEM, (slab,)), ITEM, SESSION)

    assert [d["fromqty"] for d in combo["SchemeDetails"]] == [2, 2]
    assert combo["SchemeComboOfferDetail"][0]["schemeFreeItemDetails"][0]["freeitemlinkid"] == 11
    assert none["SchemeDetails"][0]["itemLinkids"] == "11"
