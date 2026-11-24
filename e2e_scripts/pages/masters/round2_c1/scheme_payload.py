"""The body of `SchemeMaster/Save`, built the way createscheme.component.ts:1672-2005 builds it.

Enums: SchemeTypeEnum / SchemeBasisEnum / OfferTypeEnum (Globals/global.ts:20099-20122). Server side:
margerpmodel/SchemeManagement.cs (SchemeMaster, SchemeDetail), margerpdal/SchemeMasterDAL.cs:27-330.
The Applicability block is "All days, from today to the financial year end" (daytype 1, seven day rows).
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

SOURCE_WEB = 2
SAVE_ACTION = "a"
WEEK_DAYS = (1, 2, 3, 4, 5, 6, 7)


class SchemeType(IntEnum):
    ITEM_FREE_DISCOUNT = 1
    BILL_VALUE = 2
    COMBO_OFFER = 4
    BUY_X_GET_Y = 5
    RATE_WISE = 6
    NO_SCHEME = 8


class Basis(IntEnum):
    BETWEEN = 1
    AT_LEAST = 2
    EQUAL = 3


class OfferType(IntEnum):
    FREE_SAME_ITEM = 1
    RATE = 2
    SAME_DISCOUNT_PERCENT = 3
    DIFF_DISCOUNT_PERCENT = 5


class Criteria(IntEnum):
    ITEM = 1
    COMPANY = 2


@dataclass(frozen=True)
class Slab:
    """One scheme detail line: buy `from_quantity` (basis) and get `offer_value` of the offer type."""

    basis: Basis
    from_quantity: int
    offer: OfferType
    offer_value: int
    from_amount: int = 0


@dataclass(frozen=True)
class SchemeItem:
    linkid: int
    unit_linkid: int
    company_linkid: int


@dataclass(frozen=True)
class SchemeSpec:
    name: str
    kind: SchemeType
    criteria: Criteria
    slabs: tuple[Slab, ...]


@dataclass(frozen=True)
class Session:
    company_linkid: int
    user_linkid: int
    user_name: str
    store_linkid: int
    day_from: str
    day_to: str


@dataclass(frozen=True)
class Target:
    """Who the scheme is for and who saves it."""

    item: SchemeItem
    session: Session


def build_payload(spec: SchemeSpec, item: SchemeItem, session: Session) -> dict[str, Any]:
    return {
        **_base(session),
        "schemename": spec.name,
        "schemetype": int(spec.kind),
        "selectioncriteria": int(spec.criteria),
        "itemInclude": 0,
        "groupLinkid": 0,
        "linkid": 0,
        "SchemeApplicability": [_applicability(session)],
        "SchemeDetails": _details(spec, item, session),
        "SchemeComboOfferDetail": _combo_offers(spec, item),
        "BranchSchemeMapping": [],
    }


def _base(session: Session) -> dict[str, Any]:
    return {
        "ActionType": SAVE_ACTION,
        "isource": SOURCE_WEB,
        "complinkid": session.company_linkid,
        "userlinkid": session.user_linkid,
        "username": session.user_name,
    }


def _applicability(session: Session) -> dict[str, Any]:
    days = [{"dayid": day, "fromtime": None, "totime": None, "ActionType": SAVE_ACTION} for day in WEEK_DAYS]
    return {
        "fromdate": session.day_from,
        "todate": session.day_to,
        "fromtime": None,
        "totime": None,
        "daytype": 1,
        "daylist": days,
        "ActionType": SAVE_ACTION,
    }


def _detail(spec: SchemeSpec, slab: Slab, target: Target) -> dict[str, Any]:
    item, session = target.item, target.session
    by_company = spec.criteria is Criteria.COMPANY
    detail: dict[str, Any] = {
        "linkid": 0,
        "itemlinkid": 0 if by_company else item.linkid,
        "agencylinkid": item.company_linkid if by_company else 0,
        "basis": int(slab.basis),
        "fromqty": 0 if spec.kind is SchemeType.BILL_VALUE else slab.from_quantity,
        "toqty": 0,
        "unitlinkid": 0 if by_company else item.unit_linkid,
        "offertype": int(slab.offer),
        "offervalue": slab.offer_value,
        "fromamt": slab.from_amount,
        "toamt": 0,
        "salerate": 0,
        "totalamt": 0,
        "batchlinkid": 0,
        "storelinkid": session.store_linkid,
        "ActionType": SAVE_ACTION,
        "SchemeFreeItemDetails": [],
    }
    if slab.offer is OfferType.FREE_SAME_ITEM:
        detail["SchemeFreeItemDetails"] = [_free_same(slab, item)]
    if spec.kind is SchemeType.NO_SCHEME:
        detail.update({"itemLinkids": str(item.linkid), "basis": 0, "fromqty": 0, "offertype": 0})
    return detail


def _free_same(slab: Slab, item: SchemeItem) -> dict[str, Any]:
    return {
        "linkid": 0,
        "freeitemlinkid": item.linkid,
        "freeitemqty": slab.offer_value,
        "offervalue": slab.offer_value,
        "ActionType": SAVE_ACTION,
    }


COMBO_ROWS = 2


def _details(spec: SchemeSpec, item: SchemeItem, session: Session) -> list[dict[str, Any]]:
    """A combo has one detail per combo item (here the same item twice, so one billed item meets both)."""
    slabs = spec.slabs * COMBO_ROWS if spec.kind is SchemeType.COMBO_OFFER else spec.slabs
    return [_detail(spec, slab, Target(item, session)) for slab in slabs]


def _combo_offers(spec: SchemeSpec, item: SchemeItem) -> list[dict[str, Any]]:
    """The combo's offer: a discount on the combo item (createscheme.component.ts:1932-2003)."""
    if spec.kind is not SchemeType.COMBO_OFFER:
        return []
    slab = spec.slabs[0]
    free = {
        "linkid": 0,
        "freeitemlinkid": item.linkid,
        "freeitemqty": 0,
        "offertype": int(slab.offer),
        "offervalue": slab.offer_value,
        "ActionType": SAVE_ACTION,
    }
    return [
        {
            "linkid": 0,
            "offertype": int(slab.offer),
            "offervalue": slab.offer_value,
            "ActionType": SAVE_ACTION,
            "schemeFreeItemDetails": [free],
        }
    ]
