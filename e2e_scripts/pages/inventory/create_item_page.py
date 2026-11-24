"""Master > Inventory Master > Item > Create/F2: the Basic Info part of the Create Item form."""

import re
from decimal import Decimal
from enum import Enum

from playwright.sync_api import Locator, expect

from pages.accounting.toasts import Toasts
from pages.accounting.waiting import appears_within, disappears_within
from pages.base_page import BasePage
from pages.inventory.item_alert import ItemAlert
from pages.purchase.documents.navigation import ModuleMenu
from test_data.models import ItemMasterSpec

# Case-blind: the DOM text is lower case and CSS capitalises it on screen.
SAVED_MESSAGE = re.compile("Record Saved Successfully", re.IGNORECASE)
UPDATED_MESSAGE = re.compile("Record Updated Successfully", re.IGNORECASE)
PRODUCT_REQUIRED = "Product is required!"
OPENING_STOCK_QUESTION = "Do you want to add item Opening"
FORM_TIMEOUT_MS = 30_000
SUGGESTIONS_TIMEOUT_MS = 5_000
TYPEAHEAD_ATTEMPTS = 3
AGENCY_CLOSE_MS = 3_000
KEY_DELAY_MS = 100


class LookupField(Enum):
    """The mandatory fields filled from a master list, by element id."""

    UNIT = "unit"
    HSN = "hsn"
    TAX_CATEGORY = "taxxCategory"
    COMPANY = "txtcompName"


class TypeaheadError(AssertionError):
    def __init__(self, field_id: str, text: str) -> None:
        tries = TYPEAHEAD_ATTEMPTS
        super().__init__(f'No suggestion "{text}" appeared in field #{field_id} after {tries} tries')


class ProductOverwrittenError(AssertionError):
    def __init__(self, product: str, actual: str) -> None:
        tries = TYPEAHEAD_ATTEMPTS
        super().__init__(f'Product "{product}" was overwritten with "{actual}" in all {tries} tries')


class CreateItemPage(BasePage):
    def open(self) -> None:
        ModuleMenu(self.page).open_item_master()
        self.page.keyboard.press("F2")
        expect(self._product).to_be_visible(timeout=FORM_TIMEOUT_MS)

    def fill(self, item: ItemMasterSpec) -> None:
        self._enter_product_then_unit(item.product, item.unit)
        self.change_hsn(item.hsn)
        self._choose_suggestion(LookupField.TAX_CATEGORY, item.tax_category)
        self._choose_company(item.company)
        self.page.locator("#txtmrp").fill(str(item.mrp))
        self.change_sale_rate(item.sale_rate)

    def enter_product(self, product: str) -> None:
        self._product.fill(product)

    def change_hsn(self, hsn: str) -> None:
        self._choose_suggestion(LookupField.HSN, hsn)

    def change_sale_rate(self, rate: Decimal) -> None:
        self.page.locator("#txtratea").fill(str(rate))

    def save(self) -> None:
        self.page.locator("#btnSave").click()

    def expect_saved(self) -> None:
        Toasts(self.page).expect_success_saying(SAVED_MESSAGE)

    def expect_updated(self) -> None:
        Toasts(self.page).expect_success_saying(UPDATED_MESSAGE)

    def expect_refused_with(self, message: re.Pattern[str]) -> None:
        Toasts(self.page).expect_any_saying(message)

    def expect_product_required(self) -> None:
        expect(self.page.get_by_text(PRODUCT_REQUIRED, exact=True)).to_be_visible()

    def expect_marked_invalid(self, field: LookupField) -> None:
        # Why a class: an empty mandatory lookup shows only a bare "!" with no text, so Angular's
        # ng-invalid class on the input is the one readable sign of it.
        expect(self._lookup(field)).to_have_class(re.compile(r"\bng-invalid\b"))

    def expect_editing(self, product: str) -> None:
        expect(self._product).to_have_value(product, timeout=FORM_TIMEOUT_MS)

    def expect_opening_stock_offered(self) -> None:
        ItemAlert(self.page).expect_asking(OPENING_STOCK_QUESTION)

    def decline_opening_stock(self) -> None:
        ItemAlert(self.page).answer_no()
        expect(self._product).to_have_value("")

    @property
    def _product(self) -> Locator:
        # Why ids: the form has no test ids and its labels are not tied to the inputs.
        return self.page.locator("#txtProduct")

    def _lookup(self, field: LookupField) -> Locator:
        return self.page.locator(f"#{field.value}")

    def _enter_product_then_unit(self, product: str, unit: str) -> None:
        """Why the retry: just after the form loads it pulls focus back to Product each time Product is
        left, so keys typed into Unit can overwrite the name ("PCS" leaves product "CS"); a few
        seconds later it no longer does."""
        for _ in range(TYPEAHEAD_ATTEMPTS):
            self.enter_product(product)
            self._choose_suggestion(LookupField.UNIT, unit)
            if self._product.input_value() == product:
                return
        raise ProductOverwrittenError(product, self._product.input_value())

    def _choose_suggestion(self, field: LookupField, text: str) -> None:
        suggestion = self.page.get_by_role("listbox").get_by_role("option", name=text, exact=True)
        for _ in range(TYPEAHEAD_ATTEMPTS):
            self._type_into(field, text)
            if appears_within(suggestion, SUGGESTIONS_TIMEOUT_MS):
                suggestion.click()
                return
        raise TypeaheadError(field.value, text)

    def _type_into(self, field: LookupField, text: str) -> None:
        """Retyping is needed because the list stays shut when typing beats the load of the master."""
        box = self._lookup(field)
        box.click()
        box.fill("")
        box.press_sequentially(text, delay=KEY_DELAY_MS)

    def _choose_company(self, company: str) -> None:
        """Typing opens Select Agency; the field is not cleared first, as clearing opens a second dialog."""
        field = self._lookup(LookupField.COMPANY)
        field.click()
        field.press_sequentially(company, delay=KEY_DELAY_MS)
        agencies = self.page.get_by_role("dialog").filter(has_text="Select Agency")
        expect(agencies.get_by_role("searchbox")).to_have_value(company)
        agency = agencies.get_by_role("gridcell", name=company, exact=True)
        agency.click()
        if not disappears_within(agencies, AGENCY_CLOSE_MS):
            # Why: a click during a list redraw only highlights the row; Enter picks it.
            agency.press("Enter")
        expect(agencies).to_be_hidden()
        expect(field).to_have_value(company)
