"""
POM ke contract test -- browser ke bina.

Ye check karte hain ki page object apna waada nibha rahe hain: har page ka
header, total-label, aur zaroori methods maujood hain. UI badalne par yahi
sabse pehle tootega.
"""
import inspect

from pages import ItemPage, PartyPage, SaleBillPage
from pages.sale_bill_page import PurchaseBillPage, SaleReturnPage
from pages.transaction_form import TransactionForm


def test_list_pages_ka_header_aur_total_label_set_hai():
    for cls in (ItemPage, PartyPage):
        assert cls.HEADER, f"{cls.__name__}.HEADER khali"
        assert cls.TOTAL_LABEL, f"{cls.__name__}.TOTAL_LABEL khali"


def test_list_pages_me_zaroori_methods_hain():
    need = {"open", "search", "clear_search", "rows", "all_rows", "total", "has"}
    for cls in (ItemPage, PartyPage):
        missing = need - set(dir(cls))
        assert not missing, f"{cls.__name__} me missing: {missing}"


def test_transaction_form_me_zaroori_methods_hain():
    need = {"set_party", "get_party", "get_bill_no", "get_totals",
            "save", "close", "clear_popups", "suffix", "refresh"}
    missing = need - set(dir(TransactionForm))
    assert not missing, f"TransactionForm me missing: {missing}"


def test_har_transaction_page_ka_screen_screens_py_me_hai():
    from framework.screens import SCREENS
    for cls in (SaleBillPage, SaleReturnPage, PurchaseBillPage):
        assert cls.SCREEN in SCREENS, f"{cls.__name__}.SCREEN '{cls.SCREEN}' screens.py me nahi"


def test_save_allow_destructive_check_karta_hai():
    """save() me guard hona hi chahiye -- warna galti se live data likha jayega."""
    src = inspect.getsource(TransactionForm.save)
    assert "ALLOW_DESTRUCTIVE" in src, "save() me ALLOW_DESTRUCTIVE ka check nahi hai"
    assert "SaveBlocked" in src


def test_close_me_koi_save_nahi_hai():
    """close() kabhi data na likhe."""
    src = inspect.getsource(TransactionForm.close).lower()
    assert "btnsave" not in src, "close() me save button ka zikr -- khatarnak"
