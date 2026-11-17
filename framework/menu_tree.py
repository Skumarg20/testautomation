"""
MargBooks ka side menu -- jaisa app me hai, waisa hi yahan.

Tester ke dimaag me flat list nahi hoti. Uske dimaag me sidebar hota hai:
"Sale > Bill ke test chalao", "Master > Inventory Master ke saare test".
Isliye test bhi usi dhaanche me milne chahiye.

Ye tree dump_menus.txt aur screenshots se banaya gaya hai -- andaza nahi.
Har patte (leaf) ke saath likha hai:
    screen   -> framework/screens.py ka naam (list wala)
    create   -> "+" se khulne wale form ka naam
    kind     -> list / transaction / master  (POM kaunsa lagega)
"""
from __future__ import annotations

MENU: list[dict] = [
    {"id": "dashboard", "label": "Dashboard", "screen": "dashboard",
     "kind": "dashboard"},

    {"id": "master", "label": "Master", "children": [
        {"id": "master.accounts", "label": "Accounts Master", "children": [
            {"id": "master.accounts.ledger", "label": "Ledger",
             "screen": "party", "create": "party_create", "kind": "master"},
            {"id": "master.accounts.group", "label": "Group",
             "screen": "group", "kind": "master"},
        ]},
        {"id": "master.inventory", "label": "Inventory Master", "children": [
            {"id": "master.inventory.item", "label": "Item",
             "screen": "item", "create": "item_create", "kind": "master"},
            {"id": "master.inventory.store", "label": "Store",
             "screen": "store", "kind": "master"},
            {"id": "master.inventory.agency", "label": "Agency",
             "screen": "agency", "kind": "master"},
            {"id": "master.inventory.salt", "label": "Salt",
             "screen": "salt", "kind": "master"},
            {"id": "master.inventory.hsn", "label": "HSN/SAC",
             "screen": "hsn", "kind": "master"},
            {"id": "master.inventory.unit", "label": "Unit",
             "screen": "unit", "kind": "master"},
        ]},
        {"id": "master.rate", "label": "Rate Master", "children": [
            {"id": "master.rate.price_list", "label": "Price List",
             "screen": "price_list", "kind": "master"},
        ]},
        {"id": "master.opening", "label": "Opening Balance", "children": [
            {"id": "master.opening.stock", "label": "Stock",
             "screen": "opening_stock", "kind": "master"},
        ]},
    ]},

    {"id": "sale", "label": "Sale", "children": [
        {"id": "sale.bill", "label": "Bill", "screen": "sale_list",
         "create": "sale_bill", "kind": "transaction"},
        {"id": "sale.challan", "label": "Challan", "create": "sale_challan",
         "kind": "transaction"},
        {"id": "sale.pos", "label": "POS", "screen": "sale_pos",
         "kind": "transaction"},
        {"id": "sale.quotation", "label": "Quotation",
         "create": "sale_quotation", "kind": "transaction"},
        {"id": "sale.counter", "label": "Counter Sale",
         "screen": "counter_sale", "kind": "transaction"},
        {"id": "sale.stock_issue", "label": "Stock Issue",
         "create": "sale_stock_issue", "kind": "transaction"},
        {"id": "sale.order", "label": "Order", "create": "sale_order",
         "kind": "transaction"},
        {"id": "sale.return", "label": "Return", "create": "sale_return",
         "kind": "transaction"},
        {"id": "sale.return_challan", "label": "Return Challan",
         "create": "sale_return_challan", "kind": "transaction"},
        {"id": "sale.draft", "label": "Draft", "screen": "sale_draft",
         "kind": "list"},
        {"id": "sale.pd_cn", "label": "Price Diff. C/N", "create": "sale_pd_cn",
         "kind": "transaction"},
        {"id": "sale.pd_dn", "label": "Price Diff. D/N", "create": "sale_pd_dn",
         "kind": "transaction"},
    ]},

    {"id": "purchase", "label": "Purchase", "children": [
        {"id": "purchase.bill", "label": "Bill", "screen": "purchase_list",
         "create": "purchase_bill", "kind": "transaction"},
        {"id": "purchase.challan", "label": "Challan",
         "create": "purchase_challan", "kind": "transaction"},
        {"id": "purchase.quotation", "label": "Quotation",
         "create": "purchase_quotation", "kind": "transaction"},
        {"id": "purchase.stock_recv", "label": "Stock Receive",
         "create": "purchase_stock_recv", "kind": "transaction"},
        {"id": "purchase.order", "label": "Order",
         "create": "purchase_order", "kind": "transaction"},
        {"id": "purchase.return", "label": "Return",
         "create": "purchase_return", "kind": "transaction"},
        {"id": "purchase.return_challan", "label": "Return Challan",
         "create": "purchase_return_challan", "kind": "transaction"},
        {"id": "purchase.brk_exp", "label": "Brk/Exp Issue",
         "create": "purchase_brk_exp", "kind": "transaction"},
        {"id": "purchase.pd_cn", "label": "Price Diff. C/N",
         "create": "purchase_pd_cn", "kind": "transaction"},
        {"id": "purchase.pd_dn", "label": "Price Diff. D/N",
         "create": "purchase_pd_dn", "kind": "transaction"},
        {"id": "purchase.draft", "label": "Purchase Draft",
         "screen": "purchase_draft", "kind": "list"},
    ]},

    {"id": "accounting", "label": "Accounting Trans.", "children": [
        {"id": "accounting.receipt", "label": "Receipt", "screen": "receipt",
         "kind": "voucher"},
        {"id": "accounting.payment", "label": "Payment", "screen": "payment",
         "kind": "voucher"},
        {"id": "accounting.debit_note", "label": "Debit Note",
         "screen": "debit_note", "kind": "voucher"},
        {"id": "accounting.credit_note", "label": "Credit Note",
         "screen": "credit_note", "kind": "voucher"},
        {"id": "accounting.journal", "label": "Journal", "screen": "journal",
         "kind": "voucher"},
    ]},

    {"id": "stock", "label": "Stock Management", "children": [
        {"id": "stock.transfer", "label": "Stock Transfer",
         "screen": "stock_transfer", "kind": "transaction"},
        {"id": "stock.physical", "label": "Physical Stock",
         "screen": "physical_stock", "kind": "transaction"},
    ]},

    {"id": "report", "label": "Report", "screen": "report", "kind": "report"},
    {"id": "utilities", "label": "Utilities & Tools", "screen": "utilities",
     "kind": "other"},
]


# ---------------------------------------------------------------- helpers

def walk(nodes: list[dict] | None = None, trail: list[str] | None = None):
    """Har node par chalo -- (node, uska poora rasta) dete hue."""
    nodes = MENU if nodes is None else nodes
    trail = trail or []
    for n in nodes:
        path = trail + [n["label"]]
        yield n, path
        if n.get("children"):
            yield from walk(n["children"], path)


def leaves() -> list[dict]:
    """Sirf wo node jinke andar aur node nahi hain."""
    return [n for n, _ in walk() if not n.get("children")]


def by_id(node_id: str) -> dict | None:
    for n, _ in walk():
        if n["id"] == node_id:
            return n
    return None


def path_of(node_id: str) -> list[str]:
    for n, p in walk():
        if n["id"] == node_id:
            return p
    return []


def label_path(node_id: str) -> str:
    """'sale.bill' -> 'Sale > Bill'"""
    return " > ".join(path_of(node_id))


def screens_under(node_id: str) -> set[str]:
    """Is node (aur uske andar sab) se jude saare screen."""
    node = by_id(node_id)
    if not node:
        return set()
    out: set[str] = set()
    stack = [node]
    while stack:
        n = stack.pop()
        for key in ("screen", "create"):
            if n.get(key):
                out.add(n[key])
        stack.extend(n.get("children") or [])
    return out


def node_for_screen(screen: str) -> dict | None:
    """Screen ka naam de kar uska menu node lo."""
    for n, _ in walk():
        if n.get("screen") == screen or n.get("create") == screen:
            return n
    return None


def menu_of_screen(screen: str) -> str:
    """Screen -> 'Sale > Bill'. Na mile to khali."""
    n = node_for_screen(screen)
    return label_path(n["id"]) if n else ""


def tree_for_ui() -> list[dict]:
    """UI ke liye chhota tree -- sirf jo dikhana hai."""
    def clean(nodes):
        out = []
        for n in nodes:
            item = {"id": n["id"], "label": n["label"],
                    "kind": n.get("kind", "other")}
            if n.get("screen"):
                item["screen"] = n["screen"]
            if n.get("create"):
                item["create"] = n["create"]
            if n.get("children"):
                item["children"] = clean(n["children"])
            out.append(item)
        return out
    return clean(MENU)
