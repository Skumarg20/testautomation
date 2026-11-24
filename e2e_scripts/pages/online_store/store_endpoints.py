"""The endpoints J37's stubbed tests answer themselves, and the writes their `SendGuard` never lets out.

Sources (Angular paths relative to `newmarg-webangular20/src/app/`):
- `SaveOnlineStore` creates the company's own store and has no delete (`app-onlinestore.component.ts:722`).
- The Marg Mart tab asks Marg's BSS server for the store data, saves it with `MargMart/Save` and opens the
  registration on margmart.com (`app-onlinestore.component.ts:289-325`;
  `Services/MrgHttpService.service.ts:914`).
- `InsertOnlineStoreItems` / `HideItemFromOnlineStore` change the own store's catalogue
  (`OnlineStoreProductList.component.ts:221-270`).
- Marg Mart's product import and `Item/UploadMargMartItemdata` upload items to margmart.com
  (`OnlineStoreItemList.ts:700-779`; `MrgHttpService.service.ts:880-886`; `global.ts:18`).
- `Ledger/GetLedgerTranMultiList` is the read the conversion falls back on to find the Online Store ledger
  (fixedID 83) when the session holds no ledger list (`order-dashboard.component.ts:759-776`).
"""

import re

from pages.components.stubbed_endpoint import StubReply

SAVE_ONLINE_STORE = re.compile(r"OnlineStore/SaveOnlineStore")
MARG_MART_SAVE = re.compile(r"MargMart/Save\b")
BSS_MARG_MART_DATA = re.compile(r"bssapi\.margcompusoft\.com/api/GoDigital/GetMargmartData")
MARG_MART_PORTAL = re.compile(r"^https://margmart\.com/vendor/")
INSERT_STORE_ITEMS = re.compile(r"OnlineStore/InsertOnlineStoreItems")
HIDE_STORE_ITEMS = re.compile(r"OnlineStore/HideItemFromOnlineStore")
MARG_MART_PRODUCT_IMPORT = re.compile(
    r"importproduct\.margmart\.com/api/margmart/product-utility/erp-product-import"
)
MARG_MART_ITEM_RECORD = re.compile(r"Item/UploadMargMartItemdata")
LEDGER_BY_FIXED_ID = re.compile(r"Ledger/GetLedgerTranMultiList")
STATUS_UPDATE = re.compile(r"OnlineStore/StatusUpdationOfOnlineStore")

STORE_CREATION_WRITES = re.compile(
    "|".join(p.pattern for p in (SAVE_ONLINE_STORE, MARG_MART_SAVE, BSS_MARG_MART_DATA, MARG_MART_PORTAL))
)
CATALOGUE_WRITES = re.compile(
    "|".join(
        p.pattern
        for p in (INSERT_STORE_ITEMS, HIDE_STORE_ITEMS, MARG_MART_PRODUCT_IMPORT, MARG_MART_ITEM_RECORD)
    )
)

STORE_SAVED_REPLY = StubReply({"status": "200"})
# The success check is `res.status = "200"` (an assignment, D4), so the app treats any reply as saved.
STORE_REFUSED_REPLY = StubReply({"status": "500"})
MARG_MART_SAVED_REPLY = StubReply({"status": {"status": "1"}})
BSS_STORE_DATA_REPLY = StubReply(
    {
        "Details": {
            "PageDetails": {
                "CompanyName": "QA stub store",
                "Address1": "QA stub address",
                "Address2": "",
                "Address3": "",
                "Email": "qa-online-store@example.invalid",
                "GSTIN": "",
                "WorkHrType": 1,
                "WorkingDay_Mon_Sun": "1111110",
                "RowID": 0,
            }
        }
    }
)
ITEMS_INSERTED_REPLY = StubReply({"Data": True})
ITEMS_HIDDEN_REPLY = StubReply({"status": "200"})
MARG_MART_IMPORT_REFUSED_REPLY = StubReply({"status": "0", "data": {"data": []}})
# Marg Mart accepted one product; the toast counts data.data[] (`OnlineStoreItemList.ts:748-776`).
MARG_MART_IMPORT_ONE_REPLY = StubReply(
    {"status": "1", "data": {"data": [{"productId": "QA-STUB", "mCode": "0"}]}}
)
MARG_MART_ITEMS_RECORDED_REPLY = StubReply({"status": {"status": "1"}})
NO_LEDGER_REPLY = StubReply({"status": {"status": "0"}, "Data": []})
