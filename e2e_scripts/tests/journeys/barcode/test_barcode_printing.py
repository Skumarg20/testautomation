"""J27 barcode printing: the Item List barcode icon, the Print Barcode report and their refusals.

No label is printed: the format window is opened and closed, its Print button is never pressed."""

import pytest
from playwright.sync_api import Page

from pages.barcode.barcode_printing import BarcodePrinting
from pages.barcode.print_barcode_report import PrintBarcodeReport, PrintCriteria
from test_data.barcodes import OPENING_QUANTITY
from test_data.models import ItemMasterSpec

pytestmark = [pytest.mark.p2, pytest.mark.journey("barcode-generation-scanning")]


@pytest.fixture
def printing(barcode_page: Page) -> BarcodePrinting:
    return BarcodePrinting(barcode_page)


@pytest.fixture
def report(barcode_page: Page) -> PrintBarcodeReport:
    return PrintBarcodeReport(barcode_page)


def test_barcode_icon_lists_the_item_with_its_stock_as_print_quantity(
    stocked_item: ItemMasterSpec, printing: BarcodePrinting, barcode: str
) -> None:
    printing.open_for(stocked_item.product)

    printing.expect_line(stocked_item.product, barcode, OPENING_QUANTITY)


def test_print_opens_the_format_window_with_a_preview(
    stocked_item: ItemMasterSpec, printing: BarcodePrinting
) -> None:
    printing.open_for(stocked_item.product)

    printing.open_format_window()

    printing.expect_format_choice_with_preview()
    printing.close_format_window()


def test_item_wise_search_by_barcode_finds_only_that_item(
    saved_item: ItemMasterSpec, report: PrintBarcodeReport, barcode: str
) -> None:
    report.open()
    report.choose_criteria(PrintCriteria.ITEM_WISE)

    report.search_items_by_barcode(barcode)

    report.expect_only_item(saved_item.product)


def test_item_wise_ok_without_ticking_an_item_is_refused(
    saved_item: ItemMasterSpec, report: PrintBarcodeReport, barcode: str
) -> None:
    report.open()
    report.choose_criteria(PrintCriteria.ITEM_WISE)
    report.search_items_by_barcode(barcode)

    report.confirm_selection()

    report.expect_no_item_ticked_refusal()


def test_print_with_no_item_listed_is_refused(report: PrintBarcodeReport) -> None:
    report.open()

    report.print_labels()

    report.expect_no_item_listed_refusal()
