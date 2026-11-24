"""Test data and expected values of the online-store journey (J37), each cited from scenarios/online-store.md.

Orders are seeded for the company's own Online Store through `POST v4.2/OnlineStore/SubmitOrder` (pack OS-15):
the endpoint stores `orderstatus` as free text and validates nothing, so a test can seed a Pending, a
Converted and a rejected order directly. There is no delete endpoint, so seeded orders stay behind under the
run id.
"""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

# order-dashboard.component.html:6 and .ts:369-375: the title in both store modes.
DASHBOARD_TITLE = "Online Store Dashboard"
# onlineStore.ControlRoom.Config.html option list (OS-09); default 5 = Rate A (ProfilerMaster.model.ts:529).
RATE_CAPTIONS = ("M.R.P", "Rate A", "Rate B", "Rate C", "Rate D", "Rate E", "Rate F", "Rate G", "Rate H")
DEFAULT_RATE = "Rate A"
MRP_RATE = "M.R.P"
# Commented out in online-store-setting.component.html:18-149 and onlineStore.ControlRoom.Config.html:3-118.
HIDDEN_SETTING_CAPTIONS = (
    "Accept online Orders",
    "Set Min. Order Amount",
    "Delivery Charges",
    "Add Taxes to the final cart value",
    "Custom Charges",
)
# online-store-setting.component.html header row (OS-08).
STORE_SETTING_COLUMNS = ("S.No.", "Particulars", "Action", "Help")
RATE_SELECTION = "Rate Selection"
# app-onlinestore.component.ts createForm (about 166-202), OS-03.
WHOLE_DAY_START = "09:00"
WHOLE_DAY_END = "19:00"
OPEN_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
CLOSED_DAYS = ("Sunday",)
# order-dashboard.component.ts:1446-1447 (OS-17): Pending is every status except these two.
CONVERTED = "Converted"
REJECTED = "Order Rejected"
PENDING = "Pending"
# OnlineStoreOrderItem.quantity is an int (margerpmodel/OnlineStoreNew.cs:181): seeded quantities are whole.
SEEDED_QUANTITY = 2
SEEDED_PRICE = Decimal("125.50")
SEEDED_MOBILE = "9000000001"

# Messages and figures of the scenarios scripted with stubs or as permanent tests (pack OS-04..OS-38).
STORE_CREATED = "Store Created Successfully"  # app-onlinestore.component.ts:725
STORE_NOT_CREATED = "Store not Created"  # app-onlinestore.component.ts:729
# app-onlinestore.component.ts:324
MARG_MART_REGISTRATION = "https://margmart.com/vendor/#/registration?value="
MARG_MART_SOURCE = "utm_source=MARGBOOKS"
LEDGER_NOT_FOUND = "Transaction data not found !"  # order-dashboard.component.ts:781
UPLOAD_QUESTION = "Do you really want to upload {count} item(s)?"  # OnlineStoreProductList.component.ts:218
ITEMS_UPLOADED = "Item(s) uploaded successfully"  # OnlineStoreProductList.component.ts:229
UNMAP_QUESTION = "Do you really want to unmap {count} item(s)?"  # OnlineStoreProductList.component.ts:253
ITEMS_UNMAPPED = "Item(s) unmapped successfully"  # OnlineStoreProductList.component.ts:266
HIDE_QUESTION = "Do you really want to hide this item ?"  # OnlineStoreProductList.component.ts:174
ITEM_HIDDEN = "Item Hide Successfully"  # OnlineStoreProductList.component.ts:186
MARG_MART_UPLOADED = "{count} Products successfully uploaded"  # OnlineStoreItemList.ts:776
MARG_MART_LIMIT_REACHED = "Limit Reached"  # global.ts:19418 (AlertMsg.UploadLimitReach)
RATE_B = "Rate B"
# OS-05 (Marg_Books_Test_Cases_v1.0.xlsx#MMT-005): a GSTIN with the wrong shape.
MALFORMED_GSTIN = "12ABC"


@dataclass(frozen=True)
class OrderLine:
    product_id: str
    product_name: str
    quantity: int
    price_per_unit: Decimal

    @property
    def amount(self) -> Decimal:
        return self.price_per_unit * self.quantity


@dataclass(frozen=True)
class SeededOrder:
    """One `SubmitOrder` body; `order_no` is the storeorderid the grid shows as Order No."""

    order_no: str
    customer_name: str
    status: str
    order_date: date
    lines: tuple[OrderLine, ...]
    customer_mobile: str = SEEDED_MOBILE

    @property
    def total_quantity(self) -> int:
        return sum(line.quantity for line in self.lines)

    @property
    def total_amount(self) -> Decimal:
        return sum((line.amount for line in self.lines), Decimal(0))

    @property
    def grid_date(self) -> str:
        """order-dashboard.component.ts:1541-1545 shows the order date as dd-mm-yyyy."""
        return self.order_date.strftime("%d-%m-%Y")

    def submit_body(self) -> dict[str, object]:
        """Field names of OnlineStoreOrder (margerpmodel/OnlineStoreNew.cs:141-190)."""
        address = f"{self.customer_name} address"
        return {
            "storeorderid": self.order_no,
            "orderdate": f"{self.order_date.isoformat()}T12:00:00",
            "customername": self.customer_name,
            "customeremail": "qa-online-store@example.invalid",
            "customermobile": self.customer_mobile,
            "totalamount": str(self.total_amount),
            "paymentmethod": "COD",
            "orderstatus": self.status,
            "shippingaddress": address,
            "billingaddress": address,
            "Items": [_item_body(line) for line in self.lines],
        }


@dataclass(frozen=True)
class ConvertedSale:
    """A seeded order converted into a saved sale bill (OS-19, OS-22)."""

    order: SeededOrder
    bill_number: str


@dataclass(frozen=True)
class ListedOrder:
    """A seeded order with the linkid the server gave it (OS-29)."""

    order: SeededOrder
    link_id: str


def _item_body(line: OrderLine) -> dict[str, object]:
    return {
        "productid": line.product_id,
        "productname": line.product_name,
        "quantity": line.quantity,
        "priceperunit": str(line.price_per_unit),
    }


class OnlineStoreData:
    """Run-unique orders, named QA-<run_id>-..., so no other session's orders are mistaken for ours."""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._count = 0

    def order(self, status: str, line: OrderLine) -> SeededOrder:
        return self.order_with_lines(status, (line,))

    def order_with_lines(self, status: str, lines: tuple[OrderLine, ...]) -> SeededOrder:
        self._count += 1
        name = f"QA-{self._run_id}-Order-{self._count}"
        return SeededOrder(name, f"QA-{self._run_id}-Customer-{self._count}", status, date.today(), lines)

    def order_from_mobile(self, line: OrderLine, mobile: str) -> SeededOrder:
        """A Pending order whose customer gave `mobile` (OS-24, OS-25)."""
        return replace(self.order(PENDING, line), customer_mobile=mobile)

    def unmapped_line(self) -> OrderLine:
        """A line whose product id is no item of the company: enough for the grid, not for a conversion."""
        return OrderLine(
            f"QA-{self._run_id}-SKU", f"QA-{self._run_id}-Product", SEEDED_QUANTITY, SEEDED_PRICE
        )

    @staticmethod
    def line_for_item(item_link_id: str, item_name: str) -> OrderLine:
        """A line on a real item (its linkid), which the conversion puts on the sale bill (OS-18)."""
        return OrderLine(item_link_id, item_name, SEEDED_QUANTITY, SEEDED_PRICE)
