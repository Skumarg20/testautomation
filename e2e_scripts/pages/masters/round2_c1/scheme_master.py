"""Creates and removes a Sales Promotion scheme for a test, through the API the Create Scheme screen uses.

Save: POST SchemeMaster/Save (createscheme.component.ts:2000); list: GET SchemeMaster/List returns linkid and
schemeName (SchemeMasterDAL.cs:404-437); remove: POST SchemeMaster/UpdateStatus {linkid, isactive: 2}
(schememanagement.component.ts:292-299, SchemeMasterDAL.cs:588). The item's ids come from the item list
call (`item/ListNew`, ItemListNewModel: linkid, itemcode, unitlinkid, itemcomplinkid; ItemModel.cs:2824-2860).
"""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from playwright.sync_api import Page

from pages.inventory.item_list_page import ItemListPage
from pages.masters.round2_c1.app_api import AppApi, SessionCapture
from pages.masters.round2_c1.scheme_payload import SchemeItem, SchemeSpec, build_payload

ITEM_LIST_CALL = re.compile(r"item/ListNew", re.IGNORECASE)
DELETE_STATUS = 2
MAX_PAGES = 30


class ItemNotListedError(AssertionError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Item code {code} is not in the first {MAX_PAGES} pages of the item list")


class SchemeNotListedError(AssertionError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Scheme {name} is not in the scheme list after it was saved")


class SchemeApi:
    def __init__(self, api: AppApi, request_body: dict[str, Any]) -> None:
        self._api = api
        self._item_request = request_body

    def find_item(self, code: str) -> SchemeItem:
        for page_number in range(1, MAX_PAGES + 1):
            reply = self._api.post("item/ListNew", {**self._item_request, "PageNumber": page_number})
            for row in reply["Data"]["objItemList"]:
                if str(row["itemcode"]) == code:
                    return SchemeItem(int(row["linkid"]), int(row["unitlinkid"]), int(row["itemcomplinkid"]))
        raise ItemNotListedError(code)

    def other_item(self, code: str) -> SchemeItem:
        """Any listed item whose code is not `code`."""
        reply = self._api.post("item/ListNew", {**self._item_request, "PageNumber": 1})
        for row in reply["Data"]["objItemList"]:
            if str(row["itemcode"]) != code:
                return SchemeItem(int(row["linkid"]), int(row["unitlinkid"]), int(row["itemcomplinkid"]))
        raise ItemNotListedError(f"other than {code}")

    def create(self, spec: SchemeSpec, item: SchemeItem) -> int:
        self._api.post("SchemeMaster/Save", build_payload(spec, item, self._api.session))
        for row in self._api.get("SchemeMaster/List")["Data"]:
            if row["schemeName"] == spec.name:
                return int(row["linkid"])
        raise SchemeNotListedError(spec.name)

    def remove(self, linkid: int) -> None:
        self._api.post("SchemeMaster/UpdateStatus", {"linkid": linkid, "isactive": DELETE_STATUS})


def open_scheme_api(page: Page) -> SchemeApi:
    """Opens the item list, whose own call gives the signed session and the request body to page with."""
    api, request = SessionCapture(page).during(ItemListPage(page).open, ITEM_LIST_CALL)
    body: dict[str, Any] = request.post_data_json or {}
    return SchemeApi(api, body)


@contextmanager
def scheme_created(schemes: SchemeApi, spec: SchemeSpec, item: SchemeItem) -> Iterator[int]:
    linkid = schemes.create(spec, item)
    try:
        yield linkid
    finally:
        schemes.remove(linkid)
