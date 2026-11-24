"""J39 ABHA in the sale bill (AB-01, AB-32, AB-02, AB-03): the button and its selection popup, nothing saved.

The popup's "Patient History" opens an external consent site (pack finding 1), so no test clicks an option.
"""

import pytest
from playwright.sync_api import Page

from pages.abha.sale_bill_abha import SaleBillAbha
from pages.sale.documents.bill import SaleBillDocument

pytestmark = [pytest.mark.p3, pytest.mark.journey("abha-health-flows")]


def test_sale_bill_offers_a_red_abha_button_before_a_patient_is_linked(abha_sale_bill: SaleBillAbha) -> None:
    abha_sale_bill.expect_button_offered_as_unlinked()


def test_abha_button_opens_the_selection_with_its_four_options(abha_sale_bill: SaleBillAbha) -> None:
    abha_sale_bill.open_selection()

    abha_sale_bill.expect_selection_options_for_unlinked_bill()


def test_abha_selection_closes_without_choosing(abha_sale_bill: SaleBillAbha) -> None:
    abha_sale_bill.open_selection()

    abha_sale_bill.close_selection()

    abha_sale_bill.expect_selection_closed()


def test_sale_bill_has_no_abha_button_when_the_abha_id_is_blank(chemist_without_abha_page: Page) -> None:
    SaleBillDocument(chemist_without_abha_page).open_new()

    SaleBillAbha(chemist_without_abha_page).expect_button_not_offered()


def test_sale_bill_of_another_trade_has_no_abha_button(non_chemist_page: Page) -> None:
    SaleBillDocument(non_chemist_page).open_new()

    SaleBillAbha(non_chemist_page).expect_button_not_offered()
