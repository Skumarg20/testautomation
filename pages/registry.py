"""
Menu ke har node ke liye sahi POM.

Tester ko ye nahi sochna chahiye ki "Salt ke liye kaunsi class hai". Wo menu
me se node chunta hai, aur tool khud sahi POM le aata hai.

Jahan hume khaas jaankari hai (Item, Ledger, Sale Bill) wahan khaas class.
Baaki jagah generic -- kyunki 20 screens ke liye 20 khali class likhna sirf
code badhata, kuch deta nahi.
"""
from __future__ import annotations

from framework import menu_tree
from framework.base_page import BasePage
from pages.item_page import ItemPage
from pages.list_page import ListPage
from pages.party_page import PartyPage
from pages.sale_bill_page import SaleBillPage, SaleReturnPage, PurchaseBillPage
from pages.retail_billing import RetailBillPage
from pages.voucher_page import VoucherPage

# jin screens ke liye humne khaas kaam kiya hai
SPECIAL: dict[str, type] = {
    "item": ItemPage,
    "party": PartyPage,
    "sale_bill": SaleBillPage,
    "sale_return": SaleReturnPage,
    "purchase_bill": PurchaseBillPage,
    "counter_sale": RetailBillPage,
}

# generic list pages -- har ek ka grid header aur total label
LIST_META: dict[str, dict] = {
    "group":         {"header": "Group Name", "total": "Total"},
    "store":         {"header": "Store", "total": "Total"},
    "agency":        {"header": "Company", "total": "Total"},
    "salt":          {"header": "Salt", "total": "Total"},
    "hsn":           {"header": "HSN", "total": "Total"},
    "unit":          {"header": "Unit", "total": "Total"},
    "price_list":    {"header": "Name", "total": "Total"},
    "opening_stock": {"header": "Description", "total": "Total"},
    "sale_list":     {"header": "Bill No", "total": "Total"},
    "purchase_list": {"header": "Bill No", "total": "Total"},
    "sale_draft":    {"header": "Bill No", "total": "Total"},
    "purchase_draft": {"header": "Bill No", "total": "Total"},
}

VOUCHERS = {"receipt", "payment", "journal", "debit_note", "credit_note"}


def page_for(bp: BasePage, screen: str, open_it: bool = True):
    """
    Screen ka naam do, taiyaar POM lo.

    open_it=False -> sirf object, screen kholi nahi jayegi (jab pehle se khuli ho)
    """
    cls = SPECIAL.get(screen)
    if cls:
        return cls.open(bp) if open_it else cls(bp)

    if screen in VOUCHERS:
        return (VoucherPage.open(bp, screen=screen) if open_it
                else VoucherPage(bp, screen=screen))

    meta = LIST_META.get(screen)
    if meta or screen.endswith("_list"):
        page = (ListPage.open(bp, screen=screen) if open_it
                else ListPage(bp, screen=screen))
        if meta:
            page.HEADER = meta["header"]
            page.TOTAL_LABEL = meta["total"]
        return page

    # baaki sab transaction form maan lete hain (sale/purchase ke roop)
    from pages.transaction_form import TransactionForm
    from framework.screens import open_screen
    if open_it and not open_screen(bp, screen):
        raise RuntimeError(f"'{screen}' khul nahi paya")
    form = TransactionForm(bp)
    form.clear_popups()
    return form


def page_for_menu(bp: BasePage, node_id: str, prefer_create: bool = False):
    """
    Menu node se POM. prefer_create=True -> "+" wala form kholega.

        page_for_menu(bp, "sale.bill", prefer_create=True)   -> naya Sale Bill
        page_for_menu(bp, "sale.bill")                        -> Sale Bill List
    """
    node = menu_tree.by_id(node_id)
    if not node:
        raise KeyError(f"'{node_id}' menu me nahi hai")
    screen = (node.get("create") if prefer_create else None) \
        or node.get("screen") or node.get("create")
    if not screen:
        raise KeyError(f"'{node_id}' se koi screen nahi judi -- "
                       f"ye shayad sirf ek folder node hai")
    return page_for(bp, screen)


def describe() -> list[dict]:
    """Har menu leaf ke saath uska POM -- report aur UI ke liye."""
    out = []
    for leaf in menu_tree.leaves():
        screen = leaf.get("screen") or leaf.get("create")
        if not screen:
            continue
        cls = SPECIAL.get(screen)
        kind = ("khaas: " + cls.__name__) if cls else (
            "VoucherPage" if screen in VOUCHERS else
            "ListPage" if (screen in LIST_META or screen.endswith("_list"))
            else "TransactionForm")
        out.append({
            "id": leaf["id"], "menu": menu_tree.label_path(leaf["id"]),
            "screen": screen, "create": leaf.get("create"), "pom": kind,
        })
    return out
