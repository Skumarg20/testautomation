"""Discount and rate cases. The original suite added a random 0-9 to values; these are fixed instead."""

from dataclasses import dataclass

FIXED_OFFSET = 3


@dataclass(frozen=True)
class DiscountCase:
    item_description: str
    discount1: int | None = None
    discount2: int | None = None
    volume_discount1: int | None = None
    volume_discount2: int | None = None
    party_name: str | None = None
    company_name: str | None = None


ITEM_WISE_DISCOUNT = DiscountCase(
    item_description="Amoxicillin",
    discount1=1 + FIXED_OFFSET,
    discount2=2 + FIXED_OFFSET,
    volume_discount1=3 + FIXED_OFFSET,
    volume_discount2=4 + FIXED_OFFSET,
)

AGENCY_WISE_DISCOUNT = DiscountCase(
    item_description="A To Z Ns",
    company_name="Agency Wise Discount",
    discount1=1 + FIXED_OFFSET,
    discount2=1 + FIXED_OFFSET,
    volume_discount1=1 + FIXED_OFFSET,
    volume_discount2=1 + FIXED_OFFSET,
)

LEDGER_MASTER_DISCOUNT = DiscountCase(
    item_description="A To Z Ns",
    party_name="Ledger Master Discount",
    discount1=1 + FIXED_OFFSET,
    discount2=1 + FIXED_OFFSET,
)

LEDGER_SPECIAL_DISCOUNT = DiscountCase(
    item_description="A To Z Ns",
    party_name="Special Discount",
    discount1=1 + FIXED_OFFSET,
    discount2=1 + FIXED_OFFSET,
    volume_discount1=1 + FIXED_OFFSET,
)

PARTY_WISE_AGENCY_DISCOUNT = DiscountCase(
    item_description="A To Z Ns",
    party_name="Special Discount",
    company_name="Agency Wise Discount",
    discount1=1 + FIXED_OFFSET,
    volume_discount1=1 + FIXED_OFFSET,
)


@dataclass(frozen=True)
class RateCase:
    item_description: str
    rates: dict[str, int]


RATE_VALIDATION = RateCase(
    item_description="A To Z Ns",
    rates={letter: 300 + position + FIXED_OFFSET for position, letter in enumerate("abcdefgh")},
)
