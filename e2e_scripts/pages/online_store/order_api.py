"""Seeds orders into the company's own Online Store through the app's own API, as the logged-in user.

`POST v4.2/OnlineStore/SubmitOrder` (`MargBooks.OnlineStoreAPI/Controllers/OnlineStoreController.cs:101-120`)
takes the company from the request headers. Those headers are built by the app's interceptor
(`Services/LoaderInterceptor.service.ts:47-73`, encrypted per session) and cannot be made here, so they are
captured from the dashboard's own `GetSavedOrders` call and replayed through the browser context's request
API. The captured headers hold the session's credentials: they are never logged, printed or put in a message.
The gateway base URL is taken from the same captured request, so no host is configured here.
"""

import re
from collections.abc import Callable
from typing import Any

from playwright.sync_api import APIRequestContext, APIResponse, Page

from test_data.online_store import SeededOrder

SAVED_ORDERS_CALL = re.compile(r"/OnlineStore/GetSavedOrders")
SERVICE_PREFIX = "OnlineStore/"
CAPTURE_TIMEOUT_MS = 60_000
ORDER_SAVED = "200"
LIST_OK = "1"
ITEM_PAGE_SIZE = 200
MAX_ITEM_PAGES = 50
# Headers the browser derives per request; replaying them would be wrong or refused.
NOT_REPLAYED = frozenset({"host", "content-length", "content-type", "connection", "accept-encoding"})


class OrderNotSeededError(AssertionError):
    def __init__(self, order_no: str, status: object) -> None:
        super().__init__(
            f"OnlineStore/SubmitOrder refused order {order_no}: status {status!r} (OS-15 seeding)"
        )


class ItemNotOfferedError(AssertionError):
    def __init__(self, item_name: str) -> None:
        super().__init__(
            f"OnlineStore/GetItemListForMapping does not list item {item_name!r} (OS-18 seeding)"
        )


class OrderNotListedError(AssertionError):
    def __init__(self, order_no: str) -> None:
        super().__init__(f"OnlineStore/GetSavedOrders does not list order {order_no} (OS-29 seeding)")


class OnlineStoreApi:
    def __init__(self, request: APIRequestContext, service_url: str, headers: dict[str, str]) -> None:
        self._request = request
        self._service_url = service_url
        self._headers = headers

    @classmethod
    def captured_while(cls, page: Page, open_own_store: Callable[[], None]) -> "OnlineStoreApi":
        """Runs `open_own_store` (which loads the own store's dashboard) and keeps its API call's headers."""
        with page.expect_request(SAVED_ORDERS_CALL, timeout=CAPTURE_TIMEOUT_MS) as captured:
            open_own_store()
        call = captured.value
        service_url = call.url[: call.url.index(SERVICE_PREFIX) + len(SERVICE_PREFIX)]
        return cls(page.request, service_url, _replayable(call.all_headers()))

    def submit_order(self, order: SeededOrder) -> None:
        response = self._post("SubmitOrder", order.submit_body())
        status = _json(response).get("status")
        if status != ORDER_SAVED:
            raise OrderNotSeededError(order.order_no, status)

    def item_link_id(self, item_name: str) -> str:
        """The item's linkid, which a seeded order line needs as productid to be converted (OS-18)."""
        for page_number in range(1, MAX_ITEM_PAGES + 1):
            items = self._item_page(page_number)
            match = next((item for item in items if item.get("Product") == item_name), None)
            if match is not None:
                return str(match["linkid"])
            if not items:
                break
        raise ItemNotOfferedError(item_name)

    def order_link_id(self, order_no: str) -> str:
        """The server's linkid of a seeded order (`GetSavedOrders` Data[].linkid / storeorderid); the
        dashboard reads the list with a GET (`MrgHttpService.List`)."""
        saved = self._request.get(self._service_url + "GetSavedOrders", headers=self._headers)
        orders = _json(saved).get("Data") or []
        match = next((order for order in orders if order.get("storeorderid") == order_no), None)
        if match is None:
            raise OrderNotListedError(order_no)
        return str(match["linkid"])

    def mark_converted(self, order_link_id: str) -> None:
        """Posts the sale bill's status update for an order linkid, as the bill does after its first save
        (`processout.transaction.component.ts:22088-22094`); no bill exists, so the bill linkid is 0."""
        self._post("StatusUpdationOfOnlineStore", {"linkid": order_link_id, "convertedBillLinkid": 0})

    def _item_page(self, page_number: int) -> list[dict[str, Any]]:
        body = {"type": "all", "PageNumber": page_number, "PageSize": ITEM_PAGE_SIZE}
        answer = _json(self._post("GetItemListForMapping", body))
        if answer.get("status", {}).get("status") != LIST_OK:
            return []
        return list(answer.get("Data") or [])

    def _post(self, action: str, body: dict[str, object]) -> APIResponse:
        return self._request.post(self._service_url + action, headers=self._headers, data=body)


def _replayable(headers: dict[str, str]) -> dict[str, str]:
    return {
        name: value
        for name, value in headers.items()
        if not name.startswith(":") and name.lower() not in NOT_REPLAYED
    }


def _json(response: APIResponse) -> dict[str, Any]:
    payload = response.json() if response.ok else {}
    return payload if isinstance(payload, dict) else {}
