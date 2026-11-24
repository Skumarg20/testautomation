"""The self-healing registry must not learn wrong things (a healed nav.sale once opened Sale Bill for Sale Return)."""
import yaml

from framework.base_page import BasePage


def test_css_with_a_tag_and_class_is_a_selector_not_a_registry_key():
    assert BasePage.looks_like_selector('a.dropdown-toggle:has-text("Sale")')
    assert BasePage.looks_like_selector("a.menulink")
    assert BasePage.looks_like_selector("div.modal")
    assert not BasePage.looks_like_selector("nav.sale")
    assert not BasePage.looks_like_selector("item.search")


def test_side_menu_entries_are_the_sidebar_links_only():
    d = yaml.safe_load(open("locators/margbooks.yaml", encoding="utf-8"))
    for key, sels in d["nav"].items():
        if key in ("sale", "master", "purchase", "accounting", "stock", "banking", "crm"):
            assert all(s.startswith(("a.dropdown-toggle", "a#menu")) for s in sels), (key, sels)
    assert not ({"a", "t"} & set(d)), "stray sections learned from CSS selectors"


def test_pinned_keys_are_never_rewritten():
    assert "nav." in BasePage.PINNED and "login." in BasePage.PINNED


def test_no_control_characters_in_source():
    """A "\b" written through a non-raw string became a backspace byte inside regexes three times."""
    import glob
    bad = [f for f in glob.glob("framework/*.py") + glob.glob("pages/*.py") + glob.glob("ui_studio/*.py") +
           glob.glob("tools/*.py") if "\x08" in open(f, encoding="utf-8").read()]
    assert not bad, bad
